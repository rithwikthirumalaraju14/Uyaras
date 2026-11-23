import hashlib
import secrets
import os
from fastapi import HTTPException, Request
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from .models import User, LoginSession, RateLimit, Cart, CartItem
from .db import now

PERMISSIONS = {
    "catalog": {"Owner", "Administrator", "Catalog Manager"},
    "inventory": {"Owner", "Administrator", "Catalog Manager", "Operations Manager"},
    "orders": {"Owner", "Administrator", "Operations Manager"},
    "returns": {"Owner", "Administrator", "Operations Manager", "Support Agent"},
    "settings": {"Owner", "Administrator"},
    "staff": {"Owner"},
    "read": {"Owner", "Administrator", "Catalog Manager", "Operations Manager", "Support Agent", "Read-only Analyst"},
}


def require(ok, message, status=409):
    if not ok:
        raise HTTPException(status, message)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()
    )


def matches(password, encoded):
    return secrets.compare_digest(
        hash_password(password, encoded.split(":")[0]), encoded
    )


def identity(db, request: Request, write=False):
    token = request.cookies.get("uyaras_session", "")
    s = db.get(LoginSession, digest(token)) if token else None
    require(s and s.expires > now(), "Please refresh your session.", 401)
    if write:
        require(
            secrets.compare_digest(request.headers.get("x-csrf-token", ""), s.csrf),
            "Invalid CSRF token.",
            403,
        )
        origin = request.headers.get("origin")
        require(
            not origin or origin == os.getenv("PUBLIC_ORIGIN", "http://localhost:3000"),
            "Origin not allowed.",
            403,
        )
    u = db.get(User, s.user_id) if s.user_id else None
    require(not u or u.active, "Account unavailable.", 403)
    return s, u


def customer(db, request, write=False):
    s, u = identity(db, request, write)
    require(u, "Sign in before checkout.", 401)
    return s, u


def staff(db, request, permission="read", write=False):
    s, u = customer(db, request, write)
    require(
        u.role in PERMISSIONS[permission],
        "This action is not permitted for your role.",
        403,
    )
    return u


def rotate(db, response, user=None):
    token = secrets.token_urlsafe(32)
    s = LoginSession(
        id=digest(token),
        user_id=user.id if user else None,
        csrf=secrets.token_urlsafe(32),
        expires=now() + 86400 * 7,
    )
    db.add(s)
    response.set_cookie(
        "uyaras_session",
        token,
        httponly=True,
        secure=os.getenv("APP_ENV") == "production",
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )
    return s


def cart_key(s, u):
    return u.id if u else s.id


def lock_cart(db, key):
    db.execute(insert(Cart).values(id=key, version=0).on_conflict_do_nothing())
    return db.scalar(select(Cart).where(Cart.id == key).with_for_update())


def merge_cart(db, old_key, new_key):
    if old_key == new_key:
        return
    # A deterministic lock order also covers concurrent login/merge requests.
    for key in sorted({old_key, new_key}):
        lock_cart(db, key)
    for line in db.scalars(select(CartItem).where(CartItem.cart_id == old_key)).all():
        target = db.get(CartItem, (new_key, line.sku))
        if target:
            target.quantity = min(20, target.quantity + line.quantity)
        else:
            db.add(CartItem(cart_id=new_key, sku=line.sku, quantity=line.quantity))
        db.delete(line)
    db.get(Cart, new_key).version += 1


def throttle(db, request, action, limit=40):
    key = digest((request.client.host if request.client else "local") + action)
    db.execute(
        insert(RateLimit)
        .values(key=key, count=0, expires=now() + 900)
        .on_conflict_do_nothing()
    )
    row = db.scalar(select(RateLimit).where(RateLimit.key == key).with_for_update())
    if row.expires <= now():
        row.count, row.expires = 0, now() + 900
    row.count += 1
    # Persist attempted requests, including failed logins, independently of route rollback.
    allowed = row.count <= limit
    db.commit()
    require(allowed, "Too many attempts. Try again in 15 minutes.", 429)

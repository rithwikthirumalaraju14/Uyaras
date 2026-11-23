import hashlib
import hmac
import json
import os
import secrets
import logging
import time
from pathlib import Path
from fastapi import FastAPI, Request, Response, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, func, text, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import engine_for, session, now, uid
from .models import *
from .schemas import *
from .security import *
from .catalog import (
    row_dict,
    product_view,
    visible,
    cart_view,
    settings,
    category_visible,
    catalog_query,
)
from .checkout import *
from .errors import error_response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import run_in_threadpool
from .admin_queries import admin_collection
from .pagination import page_query, page_items
from .responses import SessionView, ProductView, ProductList, OrderView, ErrorEnvelope


def create_app(engine=None):
    request_logger=logging.getLogger('uyaras.requests')
    if not request_logger.handlers:
        handler=logging.StreamHandler();handler.setFormatter(logging.Formatter('%(message)s'));request_logger.addHandler(handler)
    request_logger.setLevel(logging.INFO)
    request_logger.propagate=False
    api = FastAPI(title="Uyaras Commerce API", version="1.1.0",
        description="V1 preview. Amounts are integer INR paise. Collections return items/total/page/page_size/pages. Mutations require the session cookie and X-CSRF-Token. Production ordering remains locked.",
        responses={code: {"model": ErrorEnvelope} for code in (400,401,403,404,409,413,422,429,500,503)})
    api.state.engine = engine if engine is not None else engine_for()

    # A wrapper is needed so FastAPI treats request as a Request, not a query parameter.
    def database(request: Request):
        yield from session(request)

    # Commit before sending success: the next request must see the saved session/order.
    DB = Depends(database, scope="function")

    @api.middleware("http")
    async def headers(request, call_next):
        started = time.monotonic()
        request.state.request_id = uid()
        if int(request.headers.get("content-length", "0") or 0) > 2_000_000:
            return error_response(request, 413, "Request body is too large.")
        try:
            path = request.url.path
            if request.method in {"POST", "PATCH", "DELETE"} and (path.startswith("/api/v1/checkout") or path.startswith("/api/v1/orders") or path.startswith("/api/v1/admin") or path == "/api/v1/cart/estimate"):
                def limit_mutations():
                    with Session(api.state.engine) as rate_db:
                        throttle(rate_db, request, "mutation:" + digest(request.cookies.get("uyaras_session", "")), 300)
                await run_in_threadpool(limit_mutations)
            response = await call_next(request)
        except HTTPException as exc:
            response = error_response(request, exc.status_code, str(exc.detail), headers=exc.headers)
        except Exception:
            request_logger.error(json.dumps({"request_id": request.state.request_id, "error": "unhandled_request_failure"}))
            response = error_response(request, 500, "The request could not be completed. Please try again.")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if not demo_mode():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        route = request.scope.get("route")
        logging.getLogger("uyaras.requests").info(
            json.dumps(
                {
                    "request_id": response.headers["X-Request-ID"],
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            )
        )
        return response

    @api.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        return error_response(request, error.status_code, str(error.detail), headers=error.headers)

    @api.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return error_response(request, 422, "Please check the submitted fields.",
            [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in error.errors()])

    @api.exception_handler(IntegrityError)
    async def conflict(request, error):
        return error_response(request, 409, "This record conflicts with existing data. Refresh and try again.")

    @api.get("/health")
    def health(db: Session = DB):
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "postgresql",
            "mode": "preview" if demo_mode() else "production-locked",
        }

    @api.post("/api/v1/metrics/vitals")
    def vitals(data: VitalInput, request: Request, db: Session = DB):
        throttle(db, request, "vitals", 600)
        request_logger.info(json.dumps({"type": "web_vital", **data.model_dump()}))
        return {"accepted": True}

    @api.get("/api/v1/session", response_model=SessionView)
    def get_session(request: Request, response: Response, db: Session = DB):
        token = request.cookies.get("uyaras_session", "")
        s = db.get(LoginSession, digest(token)) if token else None
        if not s or s.expires <= now():
            throttle(db, request, "session", 120)
            s = rotate(db, response)
        u = db.get(User, s.user_id) if s.user_id else None
        return {
            "csrf": s.csrf,
            "user": row_dict(u, ("password",)) if u and u.active else None,
            "demo": demo_mode(),
        }

    def signin(db, request, response, u):
        old, _ = identity(db, request, True)
        old_key = old.user_id or old.id
        merge_cart(db, old_key, u.id)
        db.delete(old)
        s = rotate(db, response, u)
        return {"csrf": s.csrf, "user": row_dict(u, ("password",)), "demo": demo_mode()}

    @api.post("/api/v1/auth/register")
    def register(
        data: Register, request: Request, response: Response, db: Session = DB
    ):
        identity(db, request, True)
        throttle(db, request, "register")
        u = User(
            id=uid(),
            email=data.email.lower(),
            password=hash_password(data.password),
            name=data.name,
        )
        db.add(u)
        db.flush()
        return signin(db, request, response, u)

    @api.post("/api/v1/auth/login")
    def login(data: Login, request: Request, response: Response, db: Session = DB):
        identity(db, request, True)
        throttle(db, request, "login")
        u = db.scalar(select(User).where(User.email == data.email.lower()))
        require(
            u and matches(data.password, u.password) and u.active,
            "Email or password is incorrect.",
            401,
        )
        return signin(db, request, response, u)

    @api.post("/api/v1/auth/logout")
    def logout(request: Request, response: Response, db: Session = DB):
        s, _ = identity(db, request, True)
        db.delete(s)
        new = rotate(db, response)
        return {"csrf": new.csrf, "user": None, "demo": demo_mode()}

    @api.post("/api/v1/auth/forgot")
    def forgot(data: Email, request: Request, db: Session = DB):
        identity(db, request, True)
        throttle(db, request, "forgot")
        u = db.scalar(select(User).where(User.email == data.email.lower()))
        if u:
            token = secrets.token_urlsafe(32)
            db.add(ResetToken(id=digest(token), user_id=u.id, expires=now() + 1800))
            origin = os.getenv("PUBLIC_ORIGIN", "http://localhost:3000")
            db.add(
                Outbox(
                    user_id=u.id,
                    channel="email", template="password_reset", subject="Reset your Uyaras password",
                    message=f"Reset your Uyaras password within 30 minutes: {origin}/account?token={token}",
                )
            )
        return {
            "message": "If the account exists, recovery instructions have been queued."
        }

    @api.post("/api/v1/auth/reset")
    def reset_password(data: Reset, request: Request, db: Session = DB):
        identity(db, request, True)
        throttle(db, request, "reset")
        r = db.scalar(
            select(ResetToken)
            .where(ResetToken.id == digest(data.token))
            .with_for_update()
        )
        require(r and r.expires > now(), "Recovery link is invalid or expired.", 400)
        u = db.get(User, r.user_id)
        u.password = hash_password(data.password)
        db.execute(delete(LoginSession).where(LoginSession.user_id == u.id))
        db.execute(delete(ResetToken).where(ResetToken.user_id == u.id))
        # Recovery URLs must not remain in delivery history after consumption.
        for msg in db.scalars(
            select(Outbox).where(
                Outbox.user_id == u.id, Outbox.message.like("Reset your Uyaras%")
            )
        ):
            msg.message = "Password reset completed"
            msg.status = "sent"
        return {"message": "Password updated. Sign in with your new password."}

    @api.get("/api/v1/me")
    def me(request: Request, db: Session = DB):
        _, u = customer(db, request)
        return {
            "user": row_dict(u, ("password",)),
            "addresses": [
                row_dict(a, ("user_id",))
                for a in db.scalars(select(Address).where(Address.user_id == u.id))
            ],
        }

    @api.patch("/api/v1/me")
    def profile(data: Profile, request: Request, db: Session = DB):
        _, u = customer(db, request, True)
        u.name = data.name
        return row_dict(u, ("password",))

    @api.post("/api/v1/addresses")
    def address(data: AddressInput, request: Request, db: Session = DB):
        _, u = customer(db, request, True)
        require(db.scalar(select(func.count()).select_from(Address).where(Address.user_id == u.id)) < 20, "You can save up to 20 addresses.")
        a = Address(user_id=u.id, **data.model_dump())
        db.add(a)
        db.flush()
        return row_dict(a, ("user_id",))

    @api.delete("/api/v1/addresses/{address_id}")
    def remove_address(address_id: str, request: Request, db: Session = DB):
        _, u = customer(db, request, True)
        a = db.get(Address, address_id)
        require(a and a.user_id == u.id, "Address not found.", 404)
        db.delete(a)
        return {"ok": True}

    @api.patch("/api/v1/addresses/{address_id}")
    def edit_address(address_id: str, data: AddressInput, request: Request, db: Session = DB):
        _, u = customer(db, request, True)
        a = db.get(Address, address_id)
        require(a and a.user_id == u.id, "Address not found.", 404)
        for key, value in data.model_dump().items():
            setattr(a, key, value)
        return row_dict(a, ("user_id",))

    @api.get("/api/v1/storefront")
    def storefront(db: Session = DB):
        public = settings(db)
        for key in (
            "warehouse",
            "tax_confirmed",
            "inventory_confirmed",
            "policies_confirmed",
        ):
            public.pop(key, None)
        return {**public, "demo": demo_mode(), "production_ordering": False}

    @api.get("/api/v1/categories")
    def categories(page: int = 1, page_size: int = 100, db: Session = DB):
        return page_items([row_dict(c) for c in db.scalars(select(Category).order_by(Category.name, Category.id))
                           if category_visible(db, c.id)], page, page_size)

    @api.get("/api/v1/collections")
    def collections(page: int = 1, page_size: int = 100, db: Session = DB):
        return page_query(db, select(Collection).where(Collection.published == True).order_by(Collection.name, Collection.id), page, page_size, row_dict)

    @api.get("/api/v1/offers")
    def offers(page: int = 1, page_size: int = 24, db: Session = DB):
        query = select(Promotion).where(Promotion.active == True, Promotion.used < Promotion.limit,
            or_(Promotion.start == 0, Promotion.start <= now()), or_(Promotion.end == 0, Promotion.end >= now())).order_by(Promotion.code)
        return page_query(db, query, page, page_size, lambda p: {"code": p.code, "percent": p.percent, "minimum": p.minimum, "end": p.end})

    @api.get("/api/v1/catalog/facets")
    def facets(db: Session = DB):
        categories = [c.id for c in db.scalars(select(Category)) if category_visible(db, c.id)]
        query = select(Variant).join(Product).where(Variant.active == True, Product.status == "published", Product.category_id.in_(categories))
        return {"sizes": sorted(set(db.scalars(query.with_only_columns(Variant.size)))),
                "colours": sorted(set(db.scalars(query.with_only_columns(Variant.colour))))}

    @api.get("/api/v1/products", response_model=ProductList)
    def products(
        q: str = "",
        category: str = "",
        collection: str = "",
        size: str = "",
        colour: str = "",
        sort: str = "newest",
        min_price: int = 0,
        max_price: int = 100000000,
        available: bool = False,
        page: int = 1,
        page_size: int = 24,
        db: Session = DB,
    ):
        return catalog_query(db, q, category, collection, size, colour, sort, min_price, max_price, available, page, page_size)

    @api.get("/api/v1/products/{slug}", response_model=ProductView)
    def product(slug: str, db: Session = DB):
        p = db.scalar(select(Product).where(Product.slug == slug))
        require(p and visible(db, p), "Product not found.", 404)
        return product_view(db, p)

    @api.get("/api/v1/cart")
    def get_cart(request: Request, db: Session = DB):
        s, u = identity(db, request)
        return cart_view(db, cart_key(s, u))

    @api.post("/api/v1/cart/items")
    def set_cart(data: CartInput, request: Request, db: Session = DB):
        s, u = identity(db, request, True)
        key = cart_key(s, u)
        cart = lock_cart(db, key)
        v = db.get(Variant, data.sku)
        require(
            v and v.active and visible(db, db.get(Product, v.product_id)),
            "Variant unavailable.",
            404,
        )
        line = db.get(CartItem, (key, v.sku))
        if data.quantity == 0:
            if line:
                db.delete(line)
        elif line:
            line.quantity = data.quantity
        else:
            db.add(CartItem(cart_id=key, sku=v.sku, quantity=data.quantity))
        cart.version += 1
        db.flush()
        return cart_view(db, key)

    @api.get("/api/v1/checkout/serviceability/{pin}")
    def serviceability(pin: str, db: Session = DB):
        rule = db.get(DeliveryRule, pin)
        return {
            "available": bool(rule and (demo_mode() or rule.verified)),
            "rule": row_dict(rule) if rule and (demo_mode() or rule.verified) else None,
            "demo": demo_mode(),
        }

    @api.post("/api/v1/cart/estimate")
    def cart_estimate(data: EstimateInput, request: Request, db: Session = DB):
        s, u = identity(db, request, True)
        return {**calculate_cart(db, cart_key(s, u), data.pin, data.method, data.coupon, require_stock=False),
                "estimate": True, "stock_reserved": False}

    @api.post("/api/v1/checkout/quote")
    def get_quote(data: QuoteInput, request: Request, db: Session = DB):
        _, u = customer(db, request, True)
        launch_check(db)
        cart = lock_cart(db, u.id)
        snapshot = calculate(db, u, data)
        q = Quote(
            user_id=u.id,
            cart_version=cart.version,
            snapshot=snapshot,
            expires=now() + 300,
        )
        db.add(q)
        db.flush()
        return {"id": q.id, **snapshot, "expires": q.expires}

    @api.post("/api/v1/checkout/orders", response_model=OrderView)
    def place_order(
        data: OrderInput,
        request: Request,
        idempotency_key: str = Header(default=""),
        db: Session = DB,
    ):
        _, u = customer(db, request, True)
        return order_view(db, create_order(db, u, data.quote_id, idempotency_key))

    @api.get("/api/v1/orders")
    def orders(request: Request, page: int = 1, page_size: int = 24, db: Session = DB):
        _, u = customer(db, request)
        return page_query(db, select(Order).where(Order.user_id == u.id).order_by(Order.created.desc(), Order.id), page, page_size, lambda o: order_view(db, o))

    def owned(db, request, order_id, write=False):
        _, u = customer(db, request, write)
        o = lock_order(db, order_id)
        require(o.user_id == u.id, "Order not found.", 404)
        return o

    @api.get("/api/v1/orders/{order_id}")
    def order_detail(order_id: str, request: Request, db: Session = DB):
        return order_view(db, owned(db, request, order_id))

    @api.post("/api/v1/orders/{order_id}/cancel")
    def order_cancel(order_id: str, data: CancellationInput, request: Request, db: Session = DB):
        o = owned(db, request, order_id, True)
        request_cancellation(db, o, data.reason, o.user_id)
        db.flush()
        return order_view(db, o)

    @api.post("/api/v1/orders/{order_id}/payment-retry")
    def order_retry(order_id: str, request: Request, db: Session = DB):
        launch_check(db)
        o = owned(db, request, order_id, True)
        retry_payment(db, o)
        db.flush()
        return order_view(db, o)

    @api.post("/api/v1/orders/{order_id}/mock-payment")
    def mock_payment(
        order_id: str, data: MockPayment, request: Request, db: Session = DB
    ):
        require(demo_mode(), "Test payments are disabled.", 404)
        o = owned(db, request, order_id, True)
        payment_result(db, o, data.outcome, "mock-" + uid())
        db.flush()
        return order_view(db, o)

    @api.post("/api/v1/payments/webhooks/mock")
    async def webhook(request: Request, db: Session = DB):
        require(demo_mode(), "Mock webhook disabled.", 404)
        secret = os.getenv("MOCK_WEBHOOK_SECRET", "")
        require(secret, "Webhook integration is not configured.", 503)
        raw = await request.body()
        require(len(raw) <= 10000, "Payload too large.", 413)
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        require(
            hmac.compare_digest(signature, request.headers.get("x-signature", "")),
            "Invalid webhook signature.",
            401,
        )
        try:
            data = json.loads(raw)
        except ValueError:
            raise HTTPException(422, "Invalid JSON")
        require(
            isinstance(data, dict)
            and all(
                k in data for k in ("id", "order_id", "amount", "currency", "outcome")
            ),
            "Invalid event.",
            422,
        )
        require(
            isinstance(data["id"], str)
            and 1 <= len(data["id"]) <= 100
            and data["outcome"] in ("captured", "failed"),
            "Invalid event.",
            422,
        )
        o = lock_order(db, data["order_id"])
        require(
            data["currency"] == "INR"
            and type(data["amount"]) is int
            and data["amount"] == o.totals["total"],
            "Payment amount mismatch.",
        )
        prior = db.get(Webhook, data["id"])
        bodyhash = hashlib.sha256(raw).hexdigest()
        if prior:
            require(
                prior.payload_hash == bodyhash,
                "Event ID reused with different payload.",
            )
            return {"duplicate": True}
        db.add(Webhook(id=data["id"], payload_hash=bodyhash))
        payment_result(db, o, data["outcome"], data["id"])
        return {"ok": True}

    @api.post("/api/v1/orders/{order_id}/returns")
    def returns(order_id: str, data: ReturnInput, request: Request, db: Session = DB):
        o = owned(db, request, order_id, True)
        return row_dict(request_return(db, o, data))

    @api.get("/api/v1/admin/{resource}")
    def admin_read(resource: str, request: Request, page: int = 1, page_size: int = 100, q: str = "", status: str = "", customer_id: str = "", db: Session = DB):
        u = staff(db, request)
        require(1 <= page <= 10000, "Invalid page.", 422)
        if resource == "dashboard":
            return {
                "orders": db.scalar(select(func.count()).select_from(Order)),
                "customers": db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == "Customer")
                ),
                "low_stock": db.scalar(
                    select(func.count())
                    .select_from(Inventory)
                    .where(
                        Inventory.on_hand - Inventory.reserved <= Inventory.low_stock
                    )
                ),
                "sales": db.scalar(
                    select(
                        func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0)
                    )
                    .join(Order, Order.id == OrderItem.order_id)
                    .where(Order.status == "Delivered")
                ),
                "mode": "Preview: no real orders",
                "production_ordering": False,
            }
        if resource == "settings":
            require(u.role in {"Owner", "Administrator"}, "Owner permission required.", 403)
            return settings(db)
        return admin_collection(db, u, resource, page, page_size, q, status, customer_id)

    @api.post("/api/v1/admin/categories")
    def save_category(data: CategoryInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        key = data.id or uid()
        parent = data.parent_id
        seen = {key}
        while parent:
            require(parent not in seen, "Category hierarchy cannot contain a cycle.")
            seen.add(parent)
            row = db.get(Category, parent)
            require(row, "Parent category missing.", 422)
            parent = row.parent_id
        row = db.get(Category, key) or Category(id=key)
        before = row_dict(row)
        for k, v in data.model_dump(exclude={"id"}).items():
            setattr(row, k, v)
        db.add(row)
        audit(db, u.id, "category_saved", key, before=before, after=row_dict(row))
        db.flush()
        return row_dict(row)

    @api.post("/api/v1/admin/collections")
    def save_collection(data: CollectionInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        key = data.id or uid()
        row = db.get(Collection, key) or Collection(id=key)
        before = {**row_dict(row), "product_ids": list(db.scalars(select(ProductCollection.product_id).where(ProductCollection.collection_id == key)))}
        for k, v in data.model_dump(exclude={"id", "product_ids"}).items():
            setattr(row, k, v)
        db.add(row)
        db.flush()
        db.execute(
            delete(ProductCollection).where(ProductCollection.collection_id == key)
        )
        for pid in set(data.product_ids):
            require(db.get(Product, pid), "Product not found.", 422)
            db.add(ProductCollection(collection_id=key, product_id=pid))
        audit(db, u.id, "collection_saved", key, before=before, after={**row_dict(row), "product_ids": sorted(set(data.product_ids))})
        return row_dict(row)

    @api.post("/api/v1/admin/products")
    def save_product(data: ProductInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        key = data.id or uid()
        require(db.get(Category, data.category_id), "Category not found.", 422)
        row = db.get(Product, key) or Product(id=key)
        before = row_dict(row)
        for k, v in data.model_dump(exclude={"id"}).items():
            setattr(row, k, v)
        db.add(row)
        audit(db, u.id, "product_saved", key, before=before, after=row_dict(row))
        db.flush()
        return product_view(db, row)

    @api.post("/api/v1/admin/variants")
    def save_variant(data: VariantInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        require(db.get(Product, data.product_id), "Product not found.", 422)
        row = db.get(Variant, data.sku)
        require(
            not row or row.product_id == data.product_id,
            "SKU belongs to another product.",
        )
        row = row or Variant(sku=data.sku)
        before = row_dict(row)
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        db.add(row)
        db.flush()
        if not db.get(Inventory, data.sku):
            db.add(Inventory(sku=data.sku))
        audit(db, u.id, "variant_saved", data.sku, before=before, after=row_dict(row))
        return row_dict(row)

    @api.post("/api/v1/admin/inventory")
    def stock(data: StockInput, request: Request, db: Session = DB):
        u = staff(db, request, "inventory", True)
        row = db.scalar(
            select(Inventory).where(Inventory.sku == data.sku).with_for_update()
        )
        require(row, "SKU not found.", 404)
        require(
            row.on_hand + data.delta >= row.reserved,
            "Adjustment would reduce stock below reservations.",
        )
        before = row_dict(row)
        row.on_hand += data.delta
        row.real_stock = data.real_stock
        row.low_stock = data.low_stock
        db.add(Movement(sku=data.sku, delta=data.delta, reason=data.reason, actor=u.id))
        audit(
            db,
            u.id,
            "stock_adjusted",
            data.sku,
            delta=data.delta,
            reason=data.reason,
            real_stock=data.real_stock,
            before=before,
            after=row_dict(row),
        )
        return row_dict(row)

    @api.post("/api/v1/admin/rules")
    def save_rule(data: RuleInput, request: Request, db: Session = DB):
        u = staff(db, request, "settings", True)
        row = db.get(DeliveryRule, data.pin) or DeliveryRule(pin=data.pin)
        before = row_dict(row)
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        db.add(row)
        audit(
            db,
            u.id,
            "delivery_rule_saved",
            data.pin,
            before=before,
            after=row_dict(row),
        )
        db.flush()
        return row_dict(row)

    @api.post("/api/v1/admin/promotions")
    def save_promo(data: PromoInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        row = db.get(Promotion, data.code) or Promotion(code=data.code)
        before = row_dict(row)
        require(
            not data.end or data.end > data.start,
            "Promotion end must follow its start.",
            422,
        )
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        db.add(row)
        audit(
            db, u.id, "promotion_saved", data.code, before=before, after=row_dict(row)
        )
        db.flush()
        return row_dict(row)

    @api.post("/api/v1/admin/settings")
    def save_settings(data: SettingsInput, request: Request, db: Session = DB):
        u = staff(db, request, "settings", True)
        require(
            not data.ordering_enabled,
            "Production checkout activation is blocked until provider acceptance and real inventory review.",
        )
        row = db.get(Setting, "store") or Setting(key="store")
        before = dict(row.value or {})
        row.value = data.model_dump()
        db.add(row)
        audit(db, u.id, "settings_saved", "store", before=before, after=row.value)
        return row.value

    @api.post("/api/v1/admin/staff")
    def save_staff(data: StaffInput, request: Request, db: Session = DB):
        u = staff(db, request, "staff", True)
        row = db.get(User, data.user_id)
        require(row, "User not found.", 404)
        require(
            row.id != u.id,
            "You cannot change your own role or disable your own account.",
        )
        before = {"role": row.role, "active": row.active}
        row.role, row.active = data.role, data.active
        db.execute(delete(LoginSession).where(LoginSession.user_id == row.id))
        audit(db, u.id, "staff_changed", row.id, before=before, after={"role": row.role, "active": row.active})
        return row_dict(row, ("password",))

    @api.post("/api/v1/admin/orders/{order_id}")
    def act_order(order_id: str, data: ActionInput, request: Request, db: Session = DB):
        u = staff(db, request, "orders", True)
        o = lock_order(db, order_id)
        order_action(db, o, data, u.id)
        db.flush()
        return order_view(db, o)

    @api.post("/api/v1/admin/orders/{order_id}/returns")
    def support_return(
        order_id: str, data: ReturnInput, request: Request, db: Session = DB
    ):
        u = staff(db, request, "returns", True)
        o = lock_order(db, order_id)
        r = request_return(db, o, data)
        audit(db, u.id, "support_return_requested", r.id)
        return row_dict(r)

    @api.post("/api/v1/admin/returns/{return_id}")
    def act_return(
        return_id: str, data: ReturnAction, request: Request, db: Session = DB
    ):
        u = staff(db, request, "returns", True)
        r = db.scalar(
            select(ReturnRequest).where(ReturnRequest.id == return_id).with_for_update()
        )
        require(r, "Return not found.", 404)
        lock_order(db, r.order_id)
        return_action(db, r, data, u.id)
        db.flush()
        return row_dict(r)

    from .media import attach_routes

    attach_routes(api, DB)
    api.mount(
        "/art",
        StaticFiles(directory=Path(__file__).resolve().parents[2] / "mock_store/art"),
        name="sample-art",
    )
    return api

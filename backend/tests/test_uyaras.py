"""Real PostgreSQL integration tests; every test has an isolated schema."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from uyaras.db import Base, now
from uyaras.main import create_app
from uyaras.models import (
    Inventory,
    User,
    Order,
    Reservation,
    Refund,
    ReturnRequest,
    Quote,
)
from uyaras.manage import seed
from uyaras.security import hash_password
from uyaras.checkout import expire_orders


@pytest.fixture
def setup(monkeypatch):
    url = os.environ["UYARAS_DATABASE_URL"]
    root = create_engine(url)
    schema = "test_" + uuid.uuid4().hex
    with root.begin() as c:
        c.execute(text("CREATE SCHEMA " + schema))
    engine = create_engine(
        make_url(url).update_query_dict({"options": "-csearch_path=" + schema})
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        seed(db)
        db.flush()
        for s in db.scalars(select(Inventory)):
            s.on_hand = 10
        db.add(
            User(
                email="owner@example.test",
                name="Owner",
                password=hash_password("owner-long-password"),
                role="Owner",
            )
        )
    app = create_app(engine)
    monkeypatch.setenv("APP_ENV", "development")
    clients = []

    def client(email=None, owner=False):
        c = TestClient(app)
        clients.append(c)
        c.headers["x-csrf-token"] = c.get("/api/v1/session").json()["csrf"]
        if email:
            data = {
                "email": email,
                "password": "owner-long-password"
                if owner
                else "customer-long-password",
            }
            if not owner:
                data["name"] = "Test customer"
            r = c.post(
                "/api/v1/auth/login" if owner else "/api/v1/auth/register", json=data
            )
            assert r.status_code == 200, r.text
            c.headers["x-csrf-token"] = r.json()["csrf"]
        return c

    yield engine, client
    for c in clients:
        c.close()
    engine.dispose()
    with root.begin() as c:
        c.execute(text("DROP SCHEMA " + schema + " CASCADE"))
    root.dispose()


def test_registration_commits_before_http_success(setup):
    engine, _ = setup
    app = create_app(engine)
    observed = []

    async def inspect_response(scope, receive, send):
        async def checked_send(message):
            if (scope.get("path") == "/api/v1/auth/register"
                    and message["type"] == "http.response.start"
                    and message["status"] == 200):
                with Session(engine) as db:
                    observed.append(db.scalar(select(User.id).where(
                        User.email == "committed@example.test")) is not None)
            await send(message)
        await app(scope, receive, checked_send)

    with TestClient(inspect_response) as client:
        csrf = client.get("/api/v1/session").json()["csrf"]
        response = client.post("/api/v1/auth/register", headers={"x-csrf-token": csrf},
                               json={"email": "committed@example.test", "name": "Committed",
                                     "password": "customer-long-password"})
        assert response.status_code == 200
        assert observed == [True]


def post(c, path, body, code=200, **kwargs):
    r = c.post("/api/v1" + path, json=body, **kwargs)
    assert r.status_code == code, r.text
    return r.json()


def quote(c, method="COD", qty=1):
    sku = c.get("/api/v1/products").json()["items"][0]["variants"][0]["sku"]
    post(c, "/cart/items", {"sku": sku, "quantity": qty})
    a = post(
        c,
        "/addresses",
        dict(
            name="Sample",
            phone="9999999999",
            line="Test Lane",
            city="Vijayawada",
            state="Andhra Pradesh",
            pin="520001",
        ),
    )
    return post(c, "/checkout/quote", dict(address_id=a["id"], method=method)), sku


def order(c, method="COD"):
    q, sku = quote(c, method)
    return post(
        c,
        "/checkout/orders",
        {"quote_id": q["id"]},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    ), sku


def test_normalized_seed_and_guest_merge(setup):
    engine, client = setup
    c = client()
    sku = c.get("/api/v1/products").json()["items"][0]["variants"][0]["sku"]
    post(c, "/cart/items", {"sku": sku, "quantity": 2})
    r = post(
        c,
        "/auth/register",
        {
            "name": "Alice",
            "email": "alice@example.test",
            "password": "a-long-password-here",
        },
    )
    c.headers["x-csrf-token"] = r["csrf"]
    assert c.get("/api/v1/cart").json()["lines"][0]["quantity"] == 2
    with engine.connect() as db:
        assert not db.execute(
            text(
                "select tablename from pg_tables where schemaname=current_schema() and tablename='commerce_state'"
            )
        ).first()


def test_security_ownership_csrf_and_roles(setup):
    engine, client = setup
    a = client("a@example.test")
    b = client("b@example.test")
    o, _ = order(a)
    assert b.get("/api/v1/orders/" + o["id"]).status_code == 404
    assert b.get("/api/v1/admin/orders").status_code == 403
    assert (
        a.post(
            "/api/v1/cart/items",
            json={"sku": "anything", "quantity": 1},
            headers={"x-csrf-token": "wrong"},
        ).status_code
        == 403
    )
    assert (
        a.post(
            "/api/v1/cart/items",
            json={"sku": "anything", "quantity": 1},
            headers={"Origin": "https://attacker.test"},
        ).status_code
        == 403
    )


def test_idempotency_cart_and_tax_snapshot(setup):
    engine, client = setup
    c = client("a@example.test")
    q, sku = quote(c)
    key = uuid.uuid4().hex
    o = post(
        c, "/checkout/orders", {"quote_id": q["id"]}, headers={"Idempotency-Key": key}
    )
    again = post(
        c, "/checkout/orders", {"quote_id": q["id"]}, headers={"Idempotency-Key": key}
    )
    assert o["id"] == again["id"]
    assert (
        o["totals"]["total"]
        == o["totals"]["subtotal"]
        + o["totals"]["shipping"]
        + o["totals"]["cod_fee"]
        - o["totals"]["discount"]
    )
    assert o["totals"]["included_tax"] > 0
    with Session(engine) as db:
        assert db.get(Inventory, sku).reserved == 1
    assert c.get("/api/v1/cart").json()["lines"] == []


def test_last_unit_concurrent_checkout(setup):
    engine, client = setup
    a = client("a@example.test")
    b = client("b@example.test")
    qa, sku = quote(a)
    qb, _ = quote(b)
    with Session(engine) as db, db.begin():
        db.get(Inventory, sku).on_hand = 1

    def submit(args):
        c, q = args
        return c.post(
            "/api/v1/checkout/orders",
            json={"quote_id": q["id"]},
            headers={"Idempotency-Key": uuid.uuid4().hex},
        ).status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(submit, [(a, qa), (b, qb)]))
    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        assert db.get(Inventory, sku).reserved == 1


def test_expiry_retry_and_late_capture(setup):
    engine, client = setup
    c = client("a@example.test")
    o, sku = order(c, "Prepaid")
    with Session(engine) as db, db.begin():
        db.get(Order, o["id"]).expires = now() - 1
    with Session(engine) as db, db.begin():
        assert expire_orders(db) == 1
    with Session(engine) as db, db.begin():
        assert expire_orders(db) == 0
    post(c, "/orders/" + o["id"] + "/payment-retry", {})
    post(c, "/orders/" + o["id"] + "/mock-payment", {"outcome": "failed"})
    late = post(c, "/orders/" + o["id"] + "/mock-payment", {"outcome": "captured"})
    assert late["status"] == "Reconciliation required"
    with Session(engine) as db:
        assert db.get(Inventory, sku).reserved == 0


def test_cod_fulfillment_returns_and_refund_caps(setup):
    engine, client = setup
    c = client("a@example.test")
    owner = client("owner@example.test", True)
    o, sku = order(c)
    for action in ("process", "pack", "ship", "deliver"):
        o = post(
            owner,
            "/admin/orders/" + o["id"],
            {"action": action, "reference": "TRACK-01"},
        )
    with Session(engine) as db:
        assert db.get(Inventory, sku).on_hand == 9
        assert db.get(Inventory, sku).reserved == 0
    for action in ("cod_collect", "cod_remit"):
        post(
            owner,
            "/admin/orders/" + o["id"],
            {"action": action, "reference": "COD-01", "amount": o["totals"]["total"]},
        )
    r = post(
        c,
        "/orders/" + o["id"] + "/returns",
        {"item_id": o["lines"][0]["id"], "quantity": 1, "reason": "Test fit issue"},
    )
    post(
        c,
        "/orders/" + o["id"] + "/returns",
        {"item_id": o["lines"][0]["id"], "quantity": 1, "reason": "Duplicate"},
        409,
    )
    post(owner, "/admin/returns/" + r["id"], {"action": "approve"})
    post(owner, "/admin/returns/" + r["id"], {"action": "receive", "restock": True})
    post(
        owner, "/admin/returns/" + r["id"], {"action": "receive", "restock": True}, 409
    )
    with Session(engine) as db:
        assert db.get(Inventory, sku).on_hand == 10
    post(
        owner,
        "/admin/orders/" + o["id"],
        {
            "action": "refund",
            "amount": o["totals"]["total"],
            "reference": "REF-01",
            "reason": "Approved return",
        },
    )
    post(
        owner,
        "/admin/orders/" + o["id"],
        {"action": "refund", "amount": 1, "reference": "REF-02", "reason": "Excess"},
        409,
    )


def test_production_is_locked_and_settings_cannot_bypass(setup, monkeypatch):
    _, client = setup
    c = client("a@example.test")
    owner = client("owner@example.test", True)
    q, _ = quote(c)
    settings = owner.get("/api/v1/admin/settings").json()
    settings["ordering_enabled"] = True
    post(owner, "/admin/settings", settings, 409)
    monkeypatch.setenv("APP_ENV", "production")
    post(
        c,
        "/checkout/orders",
        {"quote_id": q["id"]},
        503,
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )


def test_category_cycles_and_inventory_constraints(setup):
    _, client = setup
    owner = client("owner@example.test", True)
    post(
        owner,
        "/admin/categories",
        {"id": "men", "name": "Men", "slug": "men", "parent_id": "men"},
        409,
    )
    sku = owner.get("/api/v1/products").json()["items"][0]["variants"][0]["sku"]
    post(
        owner, "/admin/inventory", {"sku": sku, "delta": -11, "reason": "Too much"}, 409
    )


def test_quote_invalidated_by_price_or_cart_change(setup):
    _, client = setup
    c = client("a@example.test")
    q, sku = quote(c)
    post(c, "/cart/items", {"sku": sku, "quantity": 2})
    post(
        c,
        "/checkout/orders",
        {"quote_id": q["id"]},
        409,
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )


def test_signed_webhook_idempotency(setup, monkeypatch):
    import json, hmac, hashlib

    monkeypatch.setenv("MOCK_WEBHOOK_SECRET", "test-secret")
    _, client = setup
    c = client("a@example.test")
    o, _ = order(c, "Prepaid")
    raw = json.dumps(
        dict(
            id="event-1",
            order_id=o["id"],
            amount=o["totals"]["total"],
            currency="INR",
            outcome="captured",
        )
    )
    signature = hmac.new(b"test-secret", raw.encode(), hashlib.sha256).hexdigest()
    assert (
        c.post(
            "/api/v1/payments/webhooks/mock",
            content=raw,
            headers={"x-signature": "wrong"},
        ).status_code
        == 401
    )
    for i in range(2):
        r = c.post(
            "/api/v1/payments/webhooks/mock",
            content=raw,
            headers={"x-signature": signature},
        )
        assert r.status_code == 200, r.text
        if i:
            assert r.json()["duplicate"]


def test_recovery_single_use_and_sessions_invalidated(setup):
    from uyaras.models import Outbox

    engine, client = setup
    c = client("recovery@example.test")
    post(c, "/auth/forgot", {"email": "recovery@example.test"})
    with Session(engine) as db:
        message = db.scalar(
            select(Outbox.message).where(Outbox.message.like("Reset your Uyaras%"))
        )
    token = message.split("token=")[1]
    post(c, "/auth/reset", {"token": token, "password": "new-long-password-here"})
    assert c.get("/api/v1/me").status_code == 401
    fresh = client()
    post(
        fresh, "/auth/reset", {"token": token, "password": "another-long-password"}, 400
    )
    post(
        fresh,
        "/auth/login",
        {"email": "recovery@example.test", "password": "new-long-password-here"},
    )


def test_snapshot_survives_catalog_edits_and_relogin_preserves_cart(setup):
    from uyaras.models import Variant, Product

    engine, client = setup
    c = client("snapshot@example.test")
    o, sku = order(c)
    with Session(engine) as db, db.begin():
        v = db.get(Variant, sku)
        v.price += 10000
        db.get(Product, v.product_id).name = "Renamed product"
    saved = c.get("/api/v1/orders/" + o["id"]).json()
    assert saved["lines"][0]["name"] == o["lines"][0]["name"]
    assert saved["lines"][0]["price"] == o["lines"][0]["price"]
    post(c, "/cart/items", {"sku": sku, "quantity": 2})
    response = post(
        c,
        "/auth/login",
        {"email": "snapshot@example.test", "password": "customer-long-password"},
    )
    c.headers["x-csrf-token"] = response["csrf"]
    assert c.get("/api/v1/cart").json()["lines"][0]["quantity"] == 2


def test_promotion_eligibility_and_item_snapshot(setup):
    from uyaras.models import Variant

    engine, client = setup
    c = client("promo@example.test")
    owner = client("owner@example.test", True)
    q, sku = quote(c)
    with Session(engine) as db:
        pid = db.get(Variant, sku).product_id
    post(
        owner,
        "/admin/promotions",
        {"code": "ONLY", "percent": 10, "minimum": 0, "eligible_products": [pid]},
    )
    q = post(
        c,
        "/checkout/quote",
        {"address_id": q["address"]["id"], "method": "COD", "coupon": "ONLY"},
    )
    o = post(
        c,
        "/checkout/orders",
        {"quote_id": q["id"]},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    assert sum(i["discount"] for i in o["lines"]) == o["totals"]["discount"]
    assert o["lines"][0]["included_tax"] > 0


def test_fresh_alembic_migration(monkeypatch):
    from alembic.config import Config
    from alembic import command

    url = os.environ["UYARAS_DATABASE_URL"]
    root = create_engine(url)
    schema = "migration_" + uuid.uuid4().hex
    with root.begin() as c:
        c.execute(text("CREATE SCHEMA " + schema))
    target = make_url(url).update_query_dict({"options": "-csearch_path=" + schema})
    engine = create_engine(target)
    monkeypatch.setenv(
        "UYARAS_DATABASE_URL", target.render_as_string(hide_password=False)
    )
    try:
        command.upgrade(Config("backend/alembic.ini"), "head")
        with engine.connect() as c:
            assert (
                c.execute(text("select version_num from alembic_version")).scalar_one()
                == "uyaras_0004"
            )
            assert (
                c.execute(
                    text(
                        "select count(*) from pg_indexes where schemaname=current_schema() and indexname='payment_reference_unique'"
                    )
                ).scalar_one()
                == 1
            )
        with Session(engine) as db, db.begin():
            seed(db)
        with Session(engine) as db:
            assert all(
                s.on_hand == 0 and not s.real_stock
                for s in db.scalars(select(Inventory))
            )
    finally:
        engine.dispose()
        with root.begin() as c:
            c.execute(text("DROP SCHEMA " + schema + " CASCADE"))
        root.dispose()


def test_r2_adapter_validates_and_manages_image_metadata(setup,monkeypatch):
    from io import BytesIO
    from PIL import Image
    from uyaras import media
    stream=BytesIO();Image.new('RGB',(2,2),'blue').save(stream,format='PNG');raw=stream.getvalue()
    class FakeR2:
        def generate_presigned_url(self,*args,**kwargs):return 'https://r2.example.test/signed-put'
        def head_object(self,**kwargs):return {'ContentLength':len(raw),'ContentType':'image/png'}
        def get_object(self,**kwargs):return {'Body':BytesIO(raw)}
    monkeypatch.setattr(media,'client',lambda:FakeR2())
    monkeypatch.setenv('R2_BUCKET','test-bucket');monkeypatch.setenv('R2_PUBLIC_URL','https://media.example.test')
    _,client=setup;owner=client('owner@example.test',True);shopper=client('media@example.test')
    product=owner.get('/api/v1/products').json()['items'][0]
    upload=post(owner,'/admin/media/upload',{'product_id':product['id'],'filename':'test.png','content_type':'image/png','size':len(raw),'alt':'Test image'})
    m=post(owner,'/admin/media/confirm',{'product_id':product['id'],'object_key':upload['object_key'],'alt':'Test image'})
    assert m['url'].startswith('https://media.example.test/products/')
    assert shopper.delete('/api/v1/admin/media/'+m['id']).status_code==403
    assert owner.patch('/api/v1/admin/media/'+m['id'],json={'alt':'Updated description','position':1}).status_code==200
    assert owner.delete('/api/v1/admin/media/'+m['id']).status_code==200

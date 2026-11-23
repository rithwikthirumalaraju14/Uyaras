"""Normalized commerce records. JSON is limited to immutable snapshots/configuration."""

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, uid, now


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(40), default="Customer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[int] = mapped_column(Integer)


class ResetToken(Base):
    __tablename__ = "reset_tokens"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[int] = mapped_column(Integer)


class Address(Base):
    __tablename__ = "addresses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(10))
    line: Mapped[str] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    pin: Mapped[str] = mapped_column(String(6))


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    published: Mapped[bool] = mapped_column(Boolean, default=True)


class Collection(Base):
    __tablename__ = "collections"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    care: Mapped[str] = mapped_column(Text, default="")
    fabric: Mapped[str] = mapped_column(Text, default="")
    cod_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    size_guide: Mapped[str] = mapped_column(Text, default="")
    seo_title: Mapped[str] = mapped_column(String(160), default="")
    seo_description: Mapped[str] = mapped_column(String(320), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)


class ProductCollection(Base):
    __tablename__ = "product_collections"
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )


class Variant(Base):
    __tablename__ = "variants"
    sku: Mapped[str] = mapped_column(String(80), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    size: Mapped[str] = mapped_column(String(20))
    colour: Mapped[str] = mapped_column(String(50))
    price: Mapped[int] = mapped_column(Integer)
    regular_price: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("product_id", "size", "colour"),
        CheckConstraint("price >= 0"),
        CheckConstraint("regular_price IS NULL OR regular_price >= price"),
    )


class Media(Base):
    __tablename__ = "media"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    alt: Mapped[str] = mapped_column(String(200))
    object_key: Mapped[str] = mapped_column(String(300), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)


class Inventory(Base):
    __tablename__ = "inventory"
    sku: Mapped[str] = mapped_column(ForeignKey("variants.sku"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    low_stock: Mapped[int] = mapped_column(Integer, default=3)
    real_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[str] = mapped_column(String(80), default="primary")
    __table_args__ = (
        CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand"),
    )


class Movement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    sku: Mapped[str] = mapped_column(ForeignKey("variants.sku"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    actor: Mapped[str] = mapped_column(String(32))
    created: Mapped[int] = mapped_column(Integer, default=now)


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)


class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id: Mapped[str] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True
    )
    sku: Mapped[str] = mapped_column(ForeignKey("variants.sku"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("quantity > 0 AND quantity <= 20"),)


class DeliveryRule(Base):
    __tablename__ = "delivery_rules"
    pin: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    shipping: Mapped[int] = mapped_column(Integer, default=4900)
    free_over: Mapped[int] = mapped_column(Integer, default=99900)
    cod: Mapped[bool] = mapped_column(Boolean, default=False)
    cod_fee: Mapped[int] = mapped_column(Integer, default=3900)
    cod_max: Mapped[int] = mapped_column(Integer, default=300000)
    days: Mapped[str] = mapped_column(
        String(100), default="3–7 working days (test estimate)"
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Promotion(Base):
    __tablename__ = "promotions"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    percent: Mapped[int] = mapped_column(Integer)
    minimum: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer, default=100)
    used: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    start: Mapped[int] = mapped_column(Integer, default=0)
    end: Mapped[int] = mapped_column(Integer, default=0)
    eligible_products: Mapped[list] = mapped_column(JSON, default=list)
    eligible_categories: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (CheckConstraint("percent >= 0 AND percent <= 100 AND used >= 0"),)


class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    cart_version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    expires: Mapped[int] = mapped_column(Integer)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30))
    payment: Mapped[str] = mapped_column(String(30))
    method: Mapped[str] = mapped_column(String(20))
    totals: Mapped[dict] = mapped_column(JSON)
    address: Mapped[dict] = mapped_column(JSON)
    coupon: Mapped[str] = mapped_column(String(40), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)
    expires: Mapped[int] = mapped_column(Integer)
    demo: Mapped[bool] = mapped_column(Boolean, default=True)
    cancellation_reason: Mapped[str] = mapped_column(String(300), default="")
    cancellation_previous: Mapped[str] = mapped_column(String(30), default="")
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    sku: Mapped[str] = mapped_column(ForeignKey("variants.sku"))
    name: Mapped[str] = mapped_column(String(150))
    size: Mapped[str] = mapped_column(String(20))
    colour: Mapped[str] = mapped_column(String(50))
    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    included_tax: Mapped[int] = mapped_column(Integer, default=0)


class Reservation(Base):
    __tablename__ = "reservations"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("inventory.sku"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="held")


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    message: Mapped[str] = mapped_column(String(300))
    actor: Mapped[str] = mapped_column(String(80), default="system")
    source: Mapped[str] = mapped_column(String(40), default="system")
    reference: Mapped[str] = mapped_column(String(100), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[int] = mapped_column(Integer, default=now)


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    amount: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(100), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)


class Webhook(Base):
    __tablename__ = "webhook_events"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    created: Mapped[int] = mapped_column(Integer, default=now)


class Shipment(Base):
    __tablename__ = "shipments"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    carrier: Mapped[str] = mapped_column(String(80))
    tracking: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="shipped")
    delivered: Mapped[int] = mapped_column(Integer, default=0)


class ReturnRequest(Base):
    __tablename__ = "return_requests"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("order_items.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(20), default="return")
    status: Mapped[str] = mapped_column(String(30), default="requested")
    restocked: Mapped[bool] = mapped_column(Boolean, default=False)
    condition: Mapped[str] = mapped_column(String(300), default="")
    resolution_reference: Mapped[str] = mapped_column(String(100), default="")
    created: Mapped[int] = mapped_column(Integer, default=now)


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(100), unique=True)
    reason: Mapped[str] = mapped_column(String(300))
    payment_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("payment_attempts.id")
    )
    created: Mapped[int] = mapped_column(Integer, default=now)
    __table_args__ = (CheckConstraint("amount > 0"),)


class CodLedger(Base):
    __tablename__ = "cod_ledger"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    due: Mapped[int] = mapped_column(Integer)
    collected: Mapped[int] = mapped_column(Integer, default=0)
    remitted: Mapped[int] = mapped_column(Integer, default=0)
    reference: Mapped[str] = mapped_column(String(100), default="")
    __table_args__ = (
        CheckConstraint("due >= collected AND collected >= remitted AND remitted >= 0"),
    )


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class Audit(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[int] = mapped_column(Integer, default=now)


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default="email")
    template: Mapped[str] = mapped_column(String(80), default="account")
    subject: Mapped[str] = mapped_column(String(200), default="Uyaras account update")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[int] = mapped_column(Integer, default=now)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires: Mapped[int] = mapped_column(Integer)

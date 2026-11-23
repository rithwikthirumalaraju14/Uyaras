from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)
    password: str = Field(min_length=12, max_length=128)


class Register(Login):
    name: str = Field(min_length=1, max_length=100)


class Email(Input):
    email: str = Field(max_length=254)


class Reset(Input):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


class Profile(Input):
    name: str = Field(min_length=1, max_length=100)


class AddressInput(Profile):
    phone: str = Field(pattern=r"^[6-9][0-9]{9}$")
    line: str = Field(min_length=3, max_length=300)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pin: str = Field(pattern=r"^[1-9][0-9]{5}$")


class CartInput(Input):
    sku: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=0, le=20, strict=True)


class QuoteInput(Input):
    address_id: str
    method: Literal["COD", "Prepaid"]
    coupon: str = Field(default="", max_length=40)


class OrderInput(Input):
    quote_id: str


class CancellationInput(Input):
    reason: str = Field(min_length=3, max_length=300)


class VitalInput(Input):
    name: Literal["LCP", "INP", "CLS", "FCP", "TTFB"]
    value: float = Field(ge=0, le=3600000, allow_inf_nan=False)
    route: Literal["home", "products", "cart", "checkout", "account", "orders", "admin", "policies", "offers", "other"]


class EstimateInput(Input):
    pin: str = Field(pattern=r"^[1-9][0-9]{5}$")
    method: Literal["COD", "Prepaid"] = "Prepaid"
    coupon: str = Field(default="", max_length=40)


class CategoryInput(Input):
    id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    parent_id: str | None = None
    published: bool = True


class CollectionInput(Input):
    id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    published: bool = True
    product_ids: list[str] = Field(default_factory=list, max_length=100)


class ProductInput(Input):
    id: str | None = None
    name: str = Field(min_length=1, max_length=150)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160)
    category_id: str
    description: str = Field(default="", max_length=10000)
    status: Literal["draft", "published", "archived"] = "draft"
    care: str = Field(default="", max_length=2000)
    fabric: str = Field(default="", max_length=2000)
    cod_allowed: bool = True
    size_guide: str = Field(default="", max_length=2000)
    seo_title: str = Field(default="", max_length=160)
    seo_description: str = Field(default="", max_length=320)


class VariantInput(Input):
    sku: str = Field(pattern=r"^[A-Za-z0-9_-]+$", max_length=80)
    product_id: str
    size: str = Field(min_length=1, max_length=20)
    colour: str = Field(min_length=1, max_length=50)
    price: int = Field(ge=0, le=10000000, strict=True)
    regular_price: int | None = Field(default=None, ge=0, le=10000000, strict=True)
    active: bool = True

    @model_validator(mode="after")
    def valid_sale(self):
        if self.regular_price is not None and self.regular_price < self.price:
            raise ValueError("Regular price cannot be below selling price.")
        return self


class StockInput(Input):
    sku: str
    delta: int = Field(ge=-100000, le=100000, strict=True)
    reason: str = Field(min_length=3, max_length=200)
    real_stock: bool = False
    low_stock: int = Field(default=3, ge=0, le=100000)


class RuleInput(Input):
    pin: str = Field(pattern=r"^[1-9][0-9]{5}$")
    name: str = Field(min_length=1, max_length=100)
    shipping: int = Field(default=4900, ge=0, le=100000)
    free_over: int = Field(default=99900, ge=0, le=10000000)
    cod: bool = False
    cod_fee: int = Field(default=3900, ge=0, le=100000)
    cod_max: int = Field(default=300000, ge=0, le=10000000)
    days: str = Field(default="3–7 working days (test estimate)", max_length=100)
    verified: bool = False


class PromoInput(Input):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", max_length=40)
    percent: int = Field(ge=1, le=100)
    minimum: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1)
    active: bool = True
    start: int = Field(default=0, ge=0)
    end: int = Field(default=0, ge=0)
    eligible_products: list[str] = Field(default_factory=list, max_length=100)
    eligible_categories: list[str] = Field(default_factory=list, max_length=100)


class SettingsInput(Input):
    brand: str = Field(default="Uyaras", min_length=1, max_length=80)
    announcement: str = Field(
        default="A little blue. A little slower. Made for your everyday.",
        max_length=200,
    )
    hero_title: str = Field(default="Find your everyday blue.", max_length=120)
    hero_text: str = Field(
        default="Easy silhouettes. Quiet colours. A softer kind of everyday.",
        max_length=300,
    )
    support_email: str = Field(default="", max_length=254)
    warehouse: str = Field(default="", max_length=500)
    return_days: int = Field(default=14, ge=0, le=90)
    returns_policy: str = Field(
        default="Preview policy: request a return within 14 days. Items must be unworn with tags. Final terms pending.",
        max_length=5000,
    )
    shipping_policy: str = Field(
        default="Preview only. Delivery coverage and dispatch estimates are not yet confirmed.",
        max_length=5000,
    )
    cancellation_policy: str = Field(
        default="Preview policy: cancellation before dispatch; paid cancellations require a recorded refund.",
        max_length=5000,
    )
    privacy_policy: str = Field(
        default="Development preview. Use fictional personal information only. Production privacy terms pending.",
        max_length=5000,
    )
    terms: str = Field(
        default="Uyaras preview: products, prices and checkout are demonstrations. No purchases are fulfilled.",
        max_length=5000,
    )
    refund_policy: str = Field(
        default="Preview policy: approved refunds are recorded against the original order after manual review. Final refund timelines and methods are pending.",
        max_length=5000,
    )
    tax_bps: int = Field(default=500, ge=0, le=4000)
    tax_confirmed: bool = False
    policies_confirmed: bool = False
    inventory_confirmed: bool = False
    ordering_enabled: bool = False


class ActionInput(Input):
    action: Literal[
        "process",
        "pack",
        "ship",
        "deliver",
        "cancel",
        "reject_cancel",
        "rto",
        "rto_receive",
        "cod_collect",
        "cod_remit",
        "refund",
        "tracking",
    ]
    reference: str = Field(default="", max_length=100)
    carrier: str = Field(default="Manual", max_length=80)
    amount: int = Field(default=0, ge=0, le=100000000)
    reason: str = Field(default="", max_length=300)
    restock: bool = False
    shipment_status: (
        Literal[
            "Picked up",
            "In transit",
            "Out for delivery",
            "Delivery failed",
            "RTO in transit",
        ]
        | None
    ) = None


class ReturnInput(Input):
    item_id: str
    quantity: int = Field(ge=1, le=20)
    reason: str = Field(min_length=3, max_length=500)
    kind: Literal["return", "exchange"] = "return"


class ReturnAction(Input):
    action: Literal["approve", "reject", "pickup", "receive", "close"]
    restock: bool = False
    reference: str = Field(default="", max_length=100)
    condition: str = Field(default="", max_length=300)


class StaffInput(Input):
    user_id: str
    role: Literal["Owner", "Administrator", "Catalog Manager", "Operations Manager", "Support Agent", "Read-only Analyst", "Customer"]
    active: bool = True


class MockPayment(Input):
    outcome: Literal["captured", "failed"]


class MediaInput(Input):
    product_id: str
    filename: str = Field(min_length=1, max_length=200)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size: int = Field(gt=0, le=10000000)
    alt: str = Field(min_length=1, max_length=200)


class MediaConfirm(Input):
    product_id: str
    object_key: str = Field(max_length=300)
    alt: str = Field(min_length=1, max_length=200)


class MediaEdit(Input):
    alt: str = Field(min_length=1, max_length=200)
    position: int = Field(ge=0, le=100)

"""Validated public response contracts. Private fields are explicitly excluded."""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class UserView(BaseModel):
    id: str
    email: str
    name: str
    role: str
    active: bool


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[dict]


class ErrorEnvelope(BaseModel):
    detail: str
    error: ErrorDetail
    request_id: str


class SessionView(BaseModel):
    csrf: str
    user: UserView | None
    demo: bool


class VariantView(BaseModel):
    sku: str
    product_id: str
    size: str
    colour: str
    price: int
    regular_price: int | None = None
    active: bool
    available: int


class MediaView(BaseModel):
    id: str
    url: str
    alt: str
    position: int


class ProductView(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    category_id: str
    category: str
    status: str
    price: int
    care: str
    fabric: str = ""
    cod_allowed: bool = True
    size_guide: str
    seo_title: str
    seo_description: str
    created: int
    variants: list[VariantView]
    images: list[MediaView]


class ProductList(BaseModel):
    items: list[ProductView]
    total: int
    page: int
    page_size: int = 24
    pages: int = 0


class TotalView(BaseModel):
    subtotal: int
    discount: int
    shipping: int
    cod_fee: int
    included_tax: int
    tax_bps: int
    total: int
    currency: Literal["INR"]


class OrderView(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    user_id: str
    status: str
    payment: str
    method: Literal["COD", "Prepaid"]
    totals: TotalView
    address: dict
    lines: list[dict]
    timeline: list[dict]
    returns: list[dict]
    refunds: list[dict]
    demo: bool

from sqlalchemy import select, func, or_
from .models import (
    Category,
    Product,
    Variant,
    Inventory,
    Media,
    Setting,
    CartItem,
    ProductCollection,
    Collection,
    Order, OrderItem,
)
from .schemas import SettingsInput
from .pagination import page_query


def row_dict(row, exclude=()):
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in exclude
    }


def settings(db):
    row = db.get(Setting, "store")
    return SettingsInput(**(row.value if row else {})).model_dump()


def category_visible(db, key, seen=None):
    seen = set() if seen is None else seen
    if key in seen:
        return False
    seen.add(key)
    c = db.get(Category, key)
    return bool(
        c
        and c.published
        and (not c.parent_id or category_visible(db, c.parent_id, seen))
    )


def visible(db, p):
    return p.status == "published" and category_visible(db, p.category_id)


def product_view(db, p):
    variants = []
    for v,stock in db.execute(
        select(Variant,Inventory).outerjoin(Inventory,Inventory.sku==Variant.sku).where(Variant.product_id == p.id).order_by(Variant.sku)
    ):
        variants.append(
            {**row_dict(v), "available": stock.on_hand - stock.reserved if stock else 0}
        )
    media = db.scalars(
        select(Media).where(Media.product_id == p.id).order_by(Media.position, Media.id)
    ).all()
    return {
        **row_dict(p),
        "variants": variants,
        "images": [row_dict(m) for m in media],
        "price": min((v["price"] for v in variants if v["active"]), default=0),
        "category": db.get(Category, p.category_id).slug,
    }


def cart_view(db, key):
    lines = []
    for line in db.scalars(
        select(CartItem).where(CartItem.cart_id == key).order_by(CartItem.sku)
    ):
        v = db.get(Variant, line.sku)
        p = db.get(Product, v.product_id)
        stock = db.get(Inventory, v.sku)
        media = db.scalar(
            select(Media)
            .where(Media.product_id == p.id)
            .order_by(Media.position)
            .limit(1)
        )
        lines.append(
            dict(
                sku=v.sku,
                name=p.name,
                slug=p.slug,
                size=v.size,
                colour=v.colour,
                price=v.price,
                regular_price=v.regular_price,
                cod_allowed=p.cod_allowed,
                quantity=line.quantity,
                available=stock.on_hand - stock.reserved,
                published=visible(db, p) and v.active,
                image=media.url if media else "",
            )
        )
    return dict(lines=lines, subtotal=sum(l["price"] * l["quantity"] for l in lines))


def catalog_query(db, q="", category="", collection="", size="", colour="", sort="newest",
                  min_price=0, max_price=100000000, available=False, page=1, page_size=24):
    categories = {c.id: c for c in db.scalars(select(Category))}
    def published(key, seen=None):
        seen = set() if seen is None else seen
        if key in seen or key not in categories: return False
        seen.add(key)
        c = categories[key]
        return c.published and (not c.parent_id or published(c.parent_id, seen))
    ids = [key for key in categories if published(key)]
    query = select(Product).where(Product.status == "published", Product.category_id.in_(ids))
    if category:
        query = query.where(Product.category_id.in_([c.id for c in categories.values() if c.slug == category]))
    if collection:
        query = query.where(Product.id.in_(select(ProductCollection.product_id).join(Collection).where(
            Collection.slug == collection, Collection.published == True)))
    if q:
        query = query.where(or_(Product.name.icontains(q, autoescape=True), Product.description.icontains(q, autoescape=True)))
    variants = select(Variant.product_id).join(Inventory).where(Variant.active == True,
        Variant.price.between(min_price, max_price))
    if size: variants = variants.where(Variant.size == size)
    if colour: variants = variants.where(func.lower(Variant.colour) == colour.lower())
    if available: variants = variants.where(Inventory.on_hand > Inventory.reserved)
    query = query.where(Product.id.in_(variants))
    price = select(func.min(Variant.price)).where(Variant.product_id == Product.id, Variant.active == True).scalar_subquery()
    if sort in ("price-asc", "price-desc"):
        query = query.order_by(price.asc() if sort == "price-asc" else price.desc())
    elif sort == "popular":
        sales = select(func.coalesce(func.sum(OrderItem.quantity), 0)).join(Variant, Variant.sku == OrderItem.sku).join(Order, Order.id == OrderItem.order_id).where(Variant.product_id == Product.id, Order.status == "Delivered").scalar_subquery()
        query = query.order_by(sales.desc())
    else: query = query.order_by(Product.created.desc())
    return page_query(db, query.order_by(Product.id), page, page_size, lambda p: product_view(db, p))

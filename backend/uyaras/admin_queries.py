"""Server-side search and pagination; resource access is checked before queries."""
from sqlalchemy import select, or_, String
from .models import *
from .catalog import row_dict, product_view
from .checkout import order_view
from .pagination import page_query
from .security import require


def admin_collection(db, user, resource, page, page_size, q, status, customer_id):
    mapping = {"products": Product, "variants": Variant, "categories": Category, "collections": Collection,
               "inventory": Inventory, "movements": Movement, "rules": DeliveryRule, "promotions": Promotion,
               "orders": Order, "customers": User, "staff": User, "outbox": Outbox, "audit": Audit,
               "returns": ReturnRequest, "refunds": Refund, "cod": CodLedger, "payments": PaymentAttempt,
               "webhooks": Webhook, "shipments": Shipment, "reservations": Reservation}
    require(resource in mapping, "Resource not found.", 404)
    role = user.role
    private = {"orders", "customers", "returns", "shipments", "reservations"}
    finance = {"payments", "refunds", "cod", "webhooks", "audit"}
    if resource == "staff": require(role == "Owner", "Owner permission required.", 403)
    if resource == "outbox": require(role in {"Owner", "Administrator"}, "Notification access restricted.", 403)
    if resource in private | finance:
        require(role in {"Owner", "Administrator", "Operations Manager", "Support Agent"}, "Resource restricted.", 403)
    model = mapping[resource]
    query = select(model)
    if resource == "customers": query = query.where(User.role == "Customer")
    if resource == "staff": query = query.where(User.role != "Customer")
    if resource == "orders" and customer_id: query = query.where(Order.user_id == customer_id)
    if status and hasattr(model, "status"): query = query.where(model.status == status)
    if q:
        fields = [column for column in model.__table__.columns if isinstance(column.type, String)
                  and column.name not in {"password", "message", "payload_hash", "object_key"}]
        conditions = [column.icontains(q, autoescape=True) for column in fields]
        if resource == "orders":
            conditions.append(Order.user_id.in_(select(User.id).where(or_(User.email.icontains(q, autoescape=True), User.name.icontains(q, autoescape=True)))))
        query = query.where(or_(*conditions))
    ordering = [model.created.desc()] if hasattr(model, "created") else []
    query = query.order_by(*ordering, *model.__table__.primary_key.columns)
    def render(row):
        if resource == "products": return product_view(db, row)
        if resource == "orders": return order_view(db, row)
        if resource == "collections":
            return {**row_dict(row), "product_ids": list(db.scalars(select(ProductCollection.product_id).where(ProductCollection.collection_id == row.id)))}
        return row_dict(row, ("password", "message", "user_id") if resource == "outbox" else ("password",))
    return page_query(db, query, page, page_size, render)

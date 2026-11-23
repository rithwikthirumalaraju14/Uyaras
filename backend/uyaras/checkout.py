"""Order state machine. Transactions lock carts, orders and individual SKU balances."""

import os
from sqlalchemy import select, delete, func
from .models import *
from .db import now, uid
from .providers import payment_provider, shipping_provider
from .security import require, lock_cart
from .catalog import cart_view, row_dict, settings


def audit(db, actor, action, target, **detail):
    db.add(Audit(actor=actor, action=action, target=target, detail=detail))


def event(db, order, message, actor="system", source="system", reference="", **detail):
    db.add(OrderEvent(order_id=order.id, message=message[:300], actor=actor, source=source, reference=reference, detail=detail))
    origin = os.getenv("PUBLIC_ORIGIN", "http://localhost:3000")
    db.add(
        Outbox(user_id=order.user_id, channel="email", template="order_update",
               subject=f"Uyaras order {order.id[:8]}: {order.status}",
               message=f"Hello,\n\n{message}\nOrder: {order.id}\nStatus: {order.status}\nPayment: {order.payment}\nTotal: INR {order.totals['total']/100:.2f}\n\nView your order: {origin}/orders/{order.id}\n\n{'Preview only: no payment or dispatch occurs.' if order.demo else 'Thank you for shopping with Uyaras.'}")
    )


def demo_mode():
    return os.getenv("APP_ENV", "development") != "production"


def launch_check(db):
    if demo_mode():
        return
    s = settings(db)
    require(
        s["ordering_enabled"]
        and s["inventory_confirmed"]
        and s["tax_confirmed"]
        and s["policies_confirmed"]
        and s["warehouse"]
        and s["support_email"],
        "Uyaras is not accepting orders yet.",
        503,
    )
    # Only mock/manual adapters are implemented in this release. This cannot be bypassed by a UI toggle.
    require(
        False, "Production provider activation and acceptance review are pending.", 503
    )


def calculate(db, user, data):
    address = db.get(Address, data.address_id)
    require(address and address.user_id == user.id, "Address not found.", 404)
    return calculate_cart(db, user.id, address.pin, data.method, data.coupon, row_dict(address, ("user_id",)))


def calculate_cart(db, key, pin, method, coupon="", address=None, require_stock=True):
    rule = db.get(DeliveryRule, pin)
    require(
        rule and (demo_mode() or rule.verified),
        "Delivery is not available for this PIN.",
    )
    cart = cart_view(db, key)
    require(cart["lines"], "Your cart is empty.")
    for line in cart["lines"]:
        require(
            line["published"] and (not require_stock or line["quantity"] <= line["available"]),
            "Availability changed. Update your cart.",
        )
    subtotal = cart["subtotal"]
    code = coupon.strip().upper()
    discount = 0
    eligible_lines = []
    if code:
        p = db.get(Promotion, code)
        require(
            p
            and p.active
            and (not p.start or p.start <= now())
            and (not p.end or p.end >= now())
            and p.used < p.limit
            and subtotal >= p.minimum,
            "Coupon is unavailable or minimum spend is not met.",
        )
        eligible = 0
        for line in cart["lines"]:
            variant = db.get(Variant, line["sku"])
            product = db.get(Product, variant.product_id)
            if (
                (not p.eligible_products and not p.eligible_categories)
                or product.id in p.eligible_products
                or product.category_id in p.eligible_categories
            ):
                eligible += line["price"] * line["quantity"]
                eligible_lines.append(line)
        require(eligible > 0, "Coupon does not apply to these items.")
        discount = eligible * p.percent // 100
    if method == "COD":
        require(
            rule.cod and subtotal - discount <= rule.cod_max and all(l["cod_allowed"] for l in cart["lines"]),
            "COD is unavailable for this order.",
        )
    shipping = (
        0 if rule.free_over and subtotal - discount >= rule.free_over else rule.shipping
    )
    cod_fee = rule.cod_fee if method == "COD" else 0
    tax_bps = settings(db)["tax_bps"]
    total = subtotal - discount + shipping + cod_fee
    if method == "COD":
        require(total <= rule.cod_max, "COD total exceeds the configured limit.")
    # Display prices include provisional tax. Split out tax; never add it twice.
    included_tax = (total * tax_bps + (10000 + tax_bps) // 2) // (10000 + tax_bps)
    line_discounts = {}
    remaining = discount
    for i, line in enumerate(eligible_lines):
        amount = remaining if i == len(eligible_lines)-1 else discount * line["price"] * line["quantity"] // eligible
        line_discounts[line["sku"]] = amount
        remaining -= amount
    return dict(
        line_discounts=line_discounts,
        lines=[
            {k: l[k] for k in ("sku", "name", "size", "colour", "price", "quantity")}
            for l in cart["lines"]
        ],
        address=address or {},
        method=method,
        coupon=code,
        totals=dict(
            subtotal=subtotal,
            discount=discount,
            shipping=shipping,
            cod_fee=cod_fee,
            included_tax=included_tax,
            tax_bps=tax_bps,
            total=total,
            currency="INR",
        ),
    )


def order_view(db, order):
    return {
        **row_dict(order),
        "lines": [
            row_dict(x)
            for x in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))
        ],
        "timeline": [
            row_dict(x)
            for x in db.scalars(
                select(OrderEvent)
                .where(OrderEvent.order_id == order.id)
                .order_by(OrderEvent.created)
            )
        ],
        "shipment": row_dict(db.get(Shipment, order.id))
        if db.get(Shipment, order.id)
        else None,
        "returns": [
            row_dict(x)
            for x in db.scalars(
                select(ReturnRequest).where(ReturnRequest.order_id == order.id)
            )
        ],
        "refunds": [
            row_dict(x)
            for x in db.scalars(select(Refund).where(Refund.order_id == order.id))
        ],
        "cod": row_dict(db.get(CodLedger, order.id))
        if db.get(CodLedger, order.id)
        else None,
    }


def lock_order(db, order_id):
    o = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    require(o, "Order not found.", 404)
    return o


def release(db, order, dispatched=False):
    holds = db.scalars(
        select(Reservation)
        .where(Reservation.order_id == order.id, Reservation.status == "held")
        .order_by(Reservation.sku)
    ).all()
    for h in holds:
        stock = db.scalar(
            select(Inventory).where(Inventory.sku == h.sku).with_for_update()
        )
        stock.reserved -= h.quantity
        if dispatched:
            stock.on_hand -= h.quantity
            db.add(
                Movement(
                    sku=h.sku,
                    delta=-h.quantity,
                    reason="Dispatch " + order.id,
                    actor="system",
                )
            )
        h.status = "dispatched" if dispatched else "released"


def create_order(db, user, quote_id, key):
    launch_check(db)
    require(
        key and 8 <= len(key) <= 100,
        "Idempotency-Key must contain 8–100 characters.",
        422,
    )
    cart = lock_cart(db, user.id)
    old = db.scalar(
        select(Order).where(Order.user_id == user.id, Order.idempotency_key == key)
    )
    if old:
        require(
            old.quote_id == quote_id, "Idempotency key was used for another request."
        )
        return old
    q = db.scalar(select(Quote).where(Quote.id == quote_id).with_for_update())
    require(q and q.user_id == user.id, "Quote not found.", 404)
    require(
        not q.consumed and q.expires > now() and q.cart_version == cart.version,
        "Quote expired or cart changed. Get a fresh quote.",
    )
    from .schemas import QuoteInput

    snap = q.snapshot
    current = calculate(
        db,
        user,
        QuoteInput(
            address_id=snap["address"]["id"],
            method=snap["method"],
            coupon=snap["coupon"],
        ),
    )
    require(current == snap, "Prices, address or rules changed. Get a fresh quote.")
    if snap["coupon"]:
        promo = db.scalar(
            select(Promotion).where(Promotion.code == snap["coupon"]).with_for_update()
        )
        require(
            promo.used < promo.limit and promo.active, "Coupon usage limit reached."
        )
        promo.used += 1
    for line in sorted(snap["lines"], key=lambda x: x["sku"]):
        stock = db.scalar(
            select(Inventory).where(Inventory.sku == line["sku"]).with_for_update()
        )
        require(
            stock.on_hand - stock.reserved >= line["quantity"],
            "This size just sold out. Update your cart.",
        )
        require(
            demo_mode() or stock.real_stock,
            "Real inventory has not been confirmed.",
            503,
        )
        stock.reserved += line["quantity"]
    o = Order(
        id=uid(),
        user_id=user.id,
        idempotency_key=key,
        quote_id=q.id,
        status="Confirmed" if snap["method"] == "COD" else "Pending payment",
        payment="COD due" if snap["method"] == "COD" else "Pending",
        method=snap["method"],
        totals=snap["totals"],
        address=snap["address"],
        coupon=snap["coupon"],
        expires=now() + 900,
        demo=demo_mode(),
    )
    db.add(o)
    db.flush()
    remaining_discount = snap["totals"]["discount"]
    eligible_lines = []
    promo = db.get(Promotion, snap["coupon"]) if snap["coupon"] else None
    for line in snap["lines"]:
        product = db.get(Product, db.get(Variant, line["sku"]).product_id)
        if promo and (
            (not promo.eligible_products and not promo.eligible_categories)
            or product.id in promo.eligible_products
            or product.category_id in promo.eligible_categories
        ):
            eligible_lines.append(line["sku"])
    eligible_total = sum(
        l["price"] * l["quantity"] for l in snap["lines"] if l["sku"] in eligible_lines
    )
    for line in snap["lines"]:
        discount = 0
        if line["sku"] in eligible_lines:
            discount = (
                remaining_discount
                if line["sku"] == eligible_lines[-1]
                else snap["totals"]["discount"]
                * line["price"]
                * line["quantity"]
                // eligible_total
            )
            remaining_discount -= discount
        tax_bps = snap["totals"]["tax_bps"]
        gross = line["price"] * line["quantity"] - discount
        db.add(
            OrderItem(
                order_id=o.id,
                discount=discount,
                included_tax=(gross * tax_bps + (10000 + tax_bps) // 2)
                // (10000 + tax_bps),
                **line,
            )
        )
        db.add(Reservation(order_id=o.id, sku=line["sku"], quantity=line["quantity"]))
    if o.method == "COD":
        db.add(CodLedger(order_id=o.id, due=o.totals["total"]))
    else:
        payment_provider().create(o.id, o.totals["total"])
        db.add(PaymentAttempt(order_id=o.id, amount=o.totals["total"]))
    q.consumed = True
    db.execute(delete(CartItem).where(CartItem.cart_id == user.id))
    cart.version += 1
    event(db, o, "Test order created" if o.demo else "Order created", user.id, "customer", after=o.status)
    db.flush()
    return o


def expire_orders(db):
    orders = db.scalars(
        select(Order)
        .where(Order.status == "Pending payment", Order.expires <= now())
        .order_by(Order.id)
        .with_for_update(skip_locked=True)
    ).all()
    for o in orders:
        release(db, o)
        o.status, o.payment = "Payment expired", "Failed"
        event(db, o, "Payment hold expired; stock released")
    return len(orders)


def payment_result(db, order, outcome, reference):
    require(order.method == "Prepaid", "This order uses COD.")
    if order.payment in (
        "Paid",
        "Captured late",
        "Refund required",
        "Refunded",
        "Partially refunded",
    ):
        return
    before = {"status": order.status, "payment": order.payment}
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.order_id == order.id)
        .order_by(PaymentAttempt.created.desc(), PaymentAttempt.id.desc())
        .limit(1)
    )
    require(attempt, "Payment attempt missing.")
    if outcome == "captured":
        if order.status != "Pending payment" or order.expires <= now():
            release(db, order)
            order.status, order.payment = "Reconciliation required", "Captured late"
        else:
            order.status, order.payment = "Confirmed", "Paid"
    elif order.status == "Pending payment":
        release(db, order)
        order.status, order.payment = "Payment failed", "Failed"
    attempt.status, attempt.reference = outcome, reference
    event(
        db,
        order,
        "Payment "
        + outcome
        + (
            " — manual reconciliation required"
            if order.payment == "Captured late"
            else ""
        ),
        actor=attempt.provider, source="payment", reference=reference,
        before=before, after={"status": order.status, "payment": order.payment},
    )


def retry_payment(db, order):
    require(
        order.method == "Prepaid"
        and order.status in ("Payment failed", "Payment expired"),
        "Payment cannot be retried.",
    )
    for h in db.scalars(
        select(Reservation)
        .where(Reservation.order_id == order.id)
        .order_by(Reservation.sku)
    ):
        stock = db.scalar(
            select(Inventory).where(Inventory.sku == h.sku).with_for_update()
        )
        require(
            stock.on_hand - stock.reserved >= h.quantity,
            "Insufficient stock for retry.",
        )
        stock.reserved += h.quantity
        h.status = "held"
    order.status, order.payment, order.expires = (
        "Pending payment",
        "Pending",
        now() + 900,
    )
    db.add(PaymentAttempt(order_id=order.id, amount=order.totals["total"]))
    event(db, order, "Payment retry started")


def request_cancellation(db, o, reason, actor):
    if o.status == "Cancellation Requested":
        return
    require(o.status in ("Pending payment", "Payment failed", "Payment expired", "Confirmed", "Processing", "Packed"),
            "Cancellation is unavailable after dispatch.")
    previous = o.status
    o.cancellation_reason, o.cancellation_previous = reason, previous
    o.status = "Cancellation Requested"
    event(db, o, "Cancellation requested: " + reason, actor, "customer", before=previous, after=o.status)
    # Unpaid attempts can be cancelled immediately; accepted orders require staff review.
    if previous in ("Pending payment", "Payment failed", "Payment expired"):
        cancel(db, o)


def cancel(db, o):
    require(
        o.status
        in (
            "Pending payment",
            "Confirmed",
            "Processing",
            "Packed",
            "Payment failed",
            "Payment expired",
            "Cancellation Requested",
        ),
        "Order cannot be cancelled after dispatch.",
    )
    release(db, o)
    o.status = "Cancelled"
    if o.payment == "Paid":
        o.payment = "Refund required"
    event(db, o, "Cancelled; any captured payment requires refund reconciliation")


def order_action(db, o, data, actor):
    before = {"status": o.status, "payment": o.payment}
    action = data.action
    states = {
        "process": ("Confirmed", "Processing"),
        "pack": ("Processing", "Packed"),
        "ship": ("Packed", "Shipped"),
        "deliver": ("Shipped", "Delivered"),
        "rto": ("Shipped", "Returning to origin"),
        "rto_receive": ("Returning to origin", "Returned to origin"),
    }
    if action in states:
        expected, after = states[action]
        require(o.status == expected, "Invalid order transition.")
        if action == "ship":
            shipping_provider()
            require(data.reference, "Tracking reference is required.", 422)
            require(
                o.payment == "Paid" or o.method == "COD",
                "Payment must be confirmed before dispatch.",
            )
            release(db, o, True)
            db.add(
                Shipment(order_id=o.id, carrier=data.carrier, tracking=data.reference)
            )
        shipment = db.get(Shipment, o.id)
        if shipment:
            shipment.status = after
            if action == "deliver":
                shipment.delivered = now()
        if action == "rto_receive" and data.restock:
            for item in db.scalars(
                select(OrderItem)
                .where(OrderItem.order_id == o.id)
                .order_by(OrderItem.sku)
            ):
                stock = db.scalar(
                    select(Inventory).where(Inventory.sku == item.sku).with_for_update()
                )
                stock.on_hand += item.quantity
                db.add(
                    Movement(
                        sku=item.sku,
                        delta=item.quantity,
                        reason="Inspected RTO " + o.id,
                        actor=actor,
                    )
                )
        o.status = after
    elif action == "cancel":
        require(data.reason or o.cancellation_reason, "A cancellation reason is required.", 422)
        o.cancellation_reason = data.reason or o.cancellation_reason
        cancel(db, o)
    elif action == "reject_cancel":
        require(o.status == "Cancellation Requested" and data.reason, "A pending request and rejection reason are required.")
        o.status = o.cancellation_previous
    elif action in ("cod_collect", "cod_remit"):
        ledger = db.get(CodLedger, o.id)
        require(
            ledger and o.status == "Delivered",
            "COD collection requires a delivered COD order.",
        )
        require(data.reference, "Reconciliation reference required.", 422)
        if action == "cod_collect":
            require(
                ledger.collected == 0 and data.amount == ledger.due,
                "Collection must equal amount due and cannot be recorded twice.",
            )
            ledger.collected = data.amount
            o.payment = "COD collected"
        else:
            require(
                ledger.remitted == 0
                and data.amount == ledger.collected
                and data.amount > 0,
                "Remittance must equal recorded collection.",
            )
            ledger.remitted = data.amount
            o.payment = "COD remitted"
        ledger.reference = data.reference
    elif action == "refund":
        require(
            o.payment
            in (
                "Paid",
                "Refund required",
                "Captured late",
                "COD collected",
                "COD remitted",
                "Partially refunded",
            ),
            "No captured payment available for refund.",
        )
        require(
            data.reference and data.reason and data.amount > 0,
            "Amount, external refund reference and reason required.",
            422,
        )
        refunded = db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.order_id == o.id
            )
        )
        require(
            refunded + data.amount <= o.totals["total"],
            "Refund exceeds collected order total.",
        )
        # This records a transfer already made externally; it never pretends to send money.
        attempt = db.scalar(
            select(PaymentAttempt)
            .where(PaymentAttempt.order_id == o.id, PaymentAttempt.status == "captured")
            .order_by(PaymentAttempt.created.desc())
            .limit(1)
        )
        db.add(
            Refund(
                order_id=o.id,
                amount=data.amount,
                reference=data.reference,
                reason=data.reason,
                payment_attempt_id=attempt.id if attempt else None,
            )
        )
        o.payment = (
            "Refunded"
            if refunded + data.amount == o.totals["total"]
            else "Partially refunded"
        )
    elif action == "tracking":
        shipment = db.get(Shipment, o.id)
        require(
            shipment and o.status in ("Shipped", "Returning to origin"),
            "Shipment is not in transit.",
        )
        allowed = {
            "shipped": {"Picked up", "In transit"},
            "Shipped": {"Picked up", "In transit"},
            "Picked up": {"In transit"},
            "In transit": {"Out for delivery", "Delivery failed"},
            "Out for delivery": {"Delivery failed"},
            "Delivery failed": {"Out for delivery", "In transit"},
            "Returning to origin": {"RTO in transit"},
        }
        require(
            data.shipment_status in allowed.get(shipment.status, set()),
            "Invalid shipment transition.",
        )
        shipment.status = data.shipment_status
        if data.reference:
            shipment.tracking = data.reference
    event(
        db,
        o,
        "Staff action: "
        + action
        + (
            ": " + data.shipment_status
            if data.shipment_status and action == "tracking"
            else ""
        ),
        actor=actor, source="staff", reference=data.reference,
        before=before, after={"status": o.status, "payment": o.payment}, reason=data.reason,
    )
    audit(
        db,
        actor,
        action,
        o.id,
        reference=data.reference,
        reason=data.reason,
        before=before,
        after={"status": o.status, "payment": o.payment},
    )


def request_return(db, o, data):
    require(o.status == "Delivered", "Returns require a delivered order.")
    shipment = db.get(Shipment, o.id)
    require(
        shipment and shipment.delivered + settings(db)["return_days"] * 86400 >= now(),
        "Return request window has closed.",
    )
    item = db.get(OrderItem, data.item_id)
    require(item and item.order_id == o.id, "Order item not found.", 404)
    used = db.scalar(
        select(func.coalesce(func.sum(ReturnRequest.quantity), 0)).where(
            ReturnRequest.item_id == item.id, ReturnRequest.status != "rejected"
        )
    )
    require(
        used + data.quantity <= item.quantity,
        "Requested quantity exceeds remaining returnable quantity.",
    )
    r = ReturnRequest(order_id=o.id, **data.model_dump())
    db.add(r)
    event(db, o, "Customer requested " + data.kind)
    db.flush()
    return r


def return_action(db, r, data, actor):
    transitions = {
        "approve": ("requested", "approved"),
        "reject": ("requested", "rejected"),
        "pickup": ("approved", "pickup arranged"),
        "receive": (("approved", "pickup arranged"), "received"),
        "close": ("received", "closed"),
    }
    before, after = transitions[data.action]
    require(
        r.status in before if isinstance(before, tuple) else r.status == before,
        "Invalid return transition.",
    )
    if data.action == "receive" and data.restock:
        item = db.get(OrderItem, r.item_id)
        stock = db.scalar(
            select(Inventory).where(Inventory.sku == item.sku).with_for_update()
        )
        stock.on_hand += r.quantity
        r.restocked = True
        db.add(
            Movement(
                sku=item.sku,
                delta=r.quantity,
                reason="Inspected return " + r.id,
                actor=actor,
            )
        )
    if data.action == "close":
        require(data.reference, "Refund or replacement order reference required.", 422)
        r.resolution_reference = data.reference
    if data.action == "pickup":
        require(data.reference, "Pickup reference required.", 422)
        r.resolution_reference = data.reference
    if data.condition:
        r.condition = data.condition
    r.status = after
    audit(db, actor, "return_" + data.action, r.id, reference=data.reference)
    event(db, db.get(Order, r.order_id), "Return " + after)

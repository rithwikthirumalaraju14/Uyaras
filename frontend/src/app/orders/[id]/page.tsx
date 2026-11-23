"use client";
import { use, useEffect, useState } from "react";
import { useStore } from "@/components/store-provider";
import { Order } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { OrderTotals } from "@/components/totals";
export default function OrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { api, ready } = useStore();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [cancellationReason, setCancellationReason] = useState("");
  useEffect(() => {
    if (ready)
      api<Order>("/orders/" + id)
        .then(setOrder)
        .catch((e) => setError(e.message));
  }, [id, ready, api]);
  async function act(path: string, body: unknown = {}) {
    try {
      setOrder(await api<Order>("/orders/" + id + path, body));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="section">
      <p className="eyebrow">ORDER DETAILS</p>
      <h1>Your everyday is taking shape.</h1>
      <p role="alert">{error}</p>
      {order && (
        <>
          <p className="notice">
            {order.demo
              ? "Test order only — no real payment or fulfillment."
              : ""}{" "}
            #{order.id.slice(0, 8)}
          </p>
          <div className="checkout-grid">
            <div>
              <h2>{order.status}</h2>
              <p>Payment: {order.payment}</p>
              {order.status === "Pending payment" && (
                <div className="tabs">
                  <Button
                    onClick={() =>
                      void act("/mock-payment", { outcome: "captured" })
                    }
                  >
                    Simulate payment success
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() =>
                      void act("/mock-payment", { outcome: "failed" })
                    }
                  >
                    Simulate failure
                  </Button>
                </div>
              )}
              {["Payment failed", "Payment expired"].includes(order.status) && (
                <Button onClick={() => void act("/payment-retry")}>
                  Retry test payment
                </Button>
              )}
              {[
                "Pending payment",
                "Confirmed",
                "Processing",
                "Packed",
                "Payment failed",
                "Payment expired",
              ].includes(order.status) && (
                <form className="form" onSubmit={e=>{e.preventDefault(); void act("/cancel", {reason:cancellationReason});}}>
                  <label>Cancellation reason<input required minLength={3} maxLength={300} value={cancellationReason} onChange={e=>setCancellationReason(e.target.value)}/></label>
                  <Button type="submit" variant="outline">Request cancellation</Button>
                </form>
              )}
              {order.lines.map((l) => (
                <div className="order-row" key={l.id}>
                  <strong>{l.name}</strong>
                  <span>
                    {l.colour} / {l.size}
                  </span>
                  <span>Qty {l.quantity}</span>
                </div>
              ))}
              {order.shipment && (
                <div className="address-card">
                  <h3>Tracking</h3>
                  <p>
                    {order.shipment.carrier}: {order.shipment.tracking}
                  </p>
                  <p>{order.shipment.status}</p>
                </div>
              )}
              <h2>Order updates</h2>
              <ol className="timeline">
                {order.timeline.map((e, i) => (
                  <li key={i}>
                    <small>
                      {new Date(e.created * 1000).toLocaleString("en-IN")}
                    </small>
                    <p>{e.message}</p>
                  </li>
                ))}
              </ol>
              {order.status === "Delivered" && (
                <form
                  className="form"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    try {
                      await api("/orders/" + id + "/returns", {
                        item_id: f.get("item"),
                        quantity: Number(f.get("quantity")),
                        reason: f.get("reason"),
                        kind: f.get("kind"),
                      });
                      setMessage("Request submitted for manual review.");
                      setOrder(await api<Order>("/orders/" + id));
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  <h2>Return or exchange</h2>
                  <label>
                    Item
                    <select name="item">
                      {order.lines.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.name} / {l.size}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Quantity
                    <input
                      name="quantity"
                      type="number"
                      min="1"
                      max="20"
                      defaultValue="1"
                      required
                    />
                  </label>
                  <label>
                    Request
                    <select name="kind">
                      <option value="return">Return</option>
                      <option value="exchange">
                        Exchange (manual arrangement)
                      </option>
                    </select>
                  </label>
                  <label>
                    Reason
                    <textarea name="reason" minLength={3} required />
                  </label>
                  <Button type="submit">Request review</Button>
                  <p role="status">{message}</p>
                </form>
              )}
              {order.returns.map((r) => (
                <p key={r.id}>
                  {r.kind}: {r.status}
                </p>
              ))}
            </div>
            <aside className="summary-box">
              <OrderTotals totals={order.totals} />
              <h3>Delivery address</h3>
              <p>
                {order.address.name}
                <br />
                {order.address.line}
                <br />
                {order.address.city}, {order.address.state} {order.address.pin}
              </p>
              {order.refunds.map((r) => (
                <p key={r.reference}>Refund recorded: {r.reference}</p>
              ))}
            </aside>
          </div>
        </>
      )}
    </section>
  );
}

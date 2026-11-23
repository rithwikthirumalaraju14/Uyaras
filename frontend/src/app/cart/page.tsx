"use client";
import Image from "next/image";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Cart, Totals, money } from "@/lib/types";
import { OrderTotals } from "@/components/totals";
import { useStore } from "@/components/store-provider";
import { Button } from "@/components/ui/button";
export default function CartPage() {
  const { api, ready } = useStore();
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState("");
  const [estimate, setEstimate] = useState<Totals | null>(null);
  const [discounts, setDiscounts] = useState<Record<string,number>>({});
  useEffect(() => {
    if (ready)
      api<Cart>("/cart")
        .then(setCart)
        .catch((e) => setError(e.message));
  }, [ready, api]);
  async function change(sku: string, quantity: number) {
    setEstimate(null);
    try {
      setCart(await api<Cart>("/cart/items", { sku, quantity }));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="section">
      <p className="eyebrow">YOUR EVERYDAY, IN THE MAKING</p>
      <h1>Your bag.</h1>
      <p role="alert">{error}</p>
      {!cart ? (
        <p>Loading your bag…</p>
      ) : !cart.lines.length ? (
        <div className="empty">
          <p>A little room for something good.</p>
          <Link className="pill-button" href="/products">
            Explore the collection
          </Link>
        </div>
      ) : (
        <div className="checkout-grid">
          <div>
            {cart.lines.map((l) => (
              <article className="cart-line" key={l.sku}>
                <Image src={l.image} alt={l.name} width={140} height={160} />
                <div>
                  <Link href={"/products/" + l.slug}>
                    <h2>{l.name}</h2>
                  </Link>
                  <p>
                    {l.colour} / {l.size}
                  </p>
                  <p>{money(l.price)}</p>
                  {estimate && !!discounts[l.sku] && <p>Coupon saving on this line: {money(discounts[l.sku])}</p>}
                  <label>
                    Quantity
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={l.quantity}
                      onChange={(e) =>
                        void change(l.sku, Number(e.target.value))
                      }
                    />
                  </label>
                  <Button variant="ghost" onClick={() => void change(l.sku, 0)}>
                    Remove
                  </Button>
                  {l.available < l.quantity && (
                    <p className="notice">
                      No stock available for this quantity. Checkout requires
                      available test stock.
                    </p>
                  )}
                </div>
                <strong>{money(l.price * l.quantity)}</strong>
              </article>
            ))}
          </div>
          <aside className="summary-box">
            <h2>A little overview</h2>
            <div className="summary-row">
              <span>Subtotal</span>
              <strong>{money(cart.subtotal)}</strong>
            </div>
            <p className="muted">
              Shipping and applicable fees calculated at checkout. Prices
              include provisional tax.
            </p>
            <form className="form" onChange={()=>setEstimate(null)} onSubmit={async e=>{
              e.preventDefault(); const fields = new FormData(e.currentTarget);
              try { const r = await api<{totals:Totals;line_discounts:Record<string,number>}>("/cart/estimate", Object.fromEntries(fields)); setEstimate(r.totals); setDiscounts(r.line_discounts); setError(""); }
              catch(e) { setEstimate(null); setError((e as Error).message); }
            }}>
              <label>Delivery PIN<input name="pin" pattern="[1-9][0-9]{5}" maxLength={6} required inputMode="numeric" /></label>
              <label>Payment preference<select name="method"><option value="Prepaid">Online payment</option><option value="COD">Cash on delivery</option></select></label>
              <label>Coupon code<input name="coupon" maxLength={40} /></label>
              <Button type="submit" variant="outline">Estimate total</Button>
            </form>
            {estimate && <div aria-live="polite"><OrderTotals totals={estimate}/><p className="muted">Estimate only. Stock and totals are checked again at checkout.</p></div>}
            <Link className="pill-button" href="/checkout">
              Continue to checkout →
            </Link>
            <p className="muted">Test orders only. No money is collected.</p>
          </aside>
        </div>
      )}
    </section>
  );
}

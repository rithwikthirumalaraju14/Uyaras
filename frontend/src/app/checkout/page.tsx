"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useStore } from "@/components/store-provider";
import { Button } from "@/components/ui/button";
import { Address, Quote, Order } from "@/lib/types";
import { AddressForm } from "@/components/address-form";
import { OrderTotals } from "@/components/totals";
export default function Checkout() {
  const { auth, ready, api } = useStore();
  const userId = auth?.user?.id;
  const router = useRouter();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressesReady, setAddressesReady] = useState(false);
  const [address, setAddress] = useState("");
  const [method, setMethod] = useState("COD");
  const [coupon, setCoupon] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState("");
  useEffect(() => {
    let active = true;
    if (userId)
      api<{ addresses: Address[] }>("/me")
        .then((r) => {
          if (!active) return;
          setAddresses(r.addresses);
          setAddress(r.addresses[0]?.id || "");
          setAddressesReady(true);
        })
        .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [userId, api]);
  if (!ready) return <section className="section">Loading…</section>;
  if (!auth?.user)
    return (
      <section className="section narrow">
        <h1>One step closer.</h1>
        <p>Sign in before final checkout. Your bag will come with you.</p>
        <Link className="pill-button" href="/account">
          Sign in or create an account →
        </Link>
      </section>
    );
  return (
    <section className="section">
      <p className="eyebrow">MAKE IT YOUR EVERYDAY</p>
      <h1>Checkout.</h1>
      <div className="notice">
        Simulation only. No real payment is taken and no order will be
        dispatched. Test delivery PINs: 500001 and 520001.
      </div>
      <p role="alert">{error}</p>
      <div className="checkout-grid">
        <div>
          <h2>1. Delivery address</h2>
          {addresses.map((a) => (
            <label className="address-card" key={a.id}>
              <input
                type="radio"
                name="address"
                checked={address === a.id}
                onChange={() => {
                  setAddress(a.id);
                  setQuote(null);
                }}
              />
              <span>
                <strong>{a.name}</strong>
                <br />
                {a.line}, {a.city}, {a.pin}
              </span>
            </label>
          ))}
          {addressesReady ? <AddressForm
            onSave={(a) => {
              setAddresses((current) => [...current, a]);
              setAddress(a.id);
              setQuote(null);
            }}
          /> : <p role="status">Loading saved addresses…</p>}
          <h2>2. Payment preference</h2>
          <div className="choices">
            {["COD", "Prepaid"].map((m) => (
              <button
                aria-pressed={method === m}
                key={m}
                onClick={() => {
                  setMethod(m);
                  setQuote(null);
                }}
              >
                {m === "COD"
                  ? "Cash on delivery (test)"
                  : "Online payment (simulation)"}
              </button>
            ))}
          </div>
          <label>
            Promotion code
            <input
              value={coupon}
              onChange={(e) => {
                setCoupon(e.target.value.toUpperCase());
                setQuote(null);
              }}
              placeholder="Optional"
            />
          </label>
          <Button
            disabled={!address || busy}
            onClick={async () => {
              setBusy(true);
              try {
                setQuote(
                  await api<Quote>("/checkout/quote", {
                    address_id: address,
                    method,
                    coupon,
                  }),
                );
                setKey(crypto.randomUUID());
                setError("");
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Review order total
          </Button>
        </div>
        <aside className="summary-box">
          <h2>3. Review & confirm</h2>
          {quote ? (
            <>
              <OrderTotals totals={quote.totals} />
              <p className="muted">
                Quote valid for five minutes. Stock is reserved only after
                confirmation.
              </p>
              <Button
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    const o = await api<Order>(
                      "/checkout/orders",
                      { quote_id: quote.id },
                      "POST",
                      { "Idempotency-Key": key },
                    );
                    router.push("/orders/" + o.id);
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Place test order
              </Button>
            </>
          ) : (
            <p>Choose an address and payment preference to get your total.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

"use client";
import Image from "next/image";
import { useState } from "react";
import Link from "next/link";
import { Product, money } from "@/lib/types";
import { useStore } from "./store-provider";
import { Button } from "@/components/ui/button";
export function ProductDetail({ product: p }: { product: Product }) {
  const { api, ready } = useStore();
  const [colour, setColour] = useState(p.variants[0]?.colour || "");
  const [size, setSize] = useState("");
  const [image, setImage] = useState(Math.max(0, p.images.findIndex(im => im.alt.toLowerCase().includes(p.variants[0]?.colour.toLowerCase() || ""))));
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [pin, setPin] = useState("");
  const [delivery, setDelivery] = useState("");
  const v = p.variants.find(
    (v) => v.colour === colour && v.size === size && v.active,
  );
  async function add() {
    if (!v) {
      setMessage("Choose your size and colour.");
      return;
    }
    setBusy(true);
    try {
      await api("/cart/items", { sku: v.sku, quantity: 1 });
      setMessage("Added to your bag.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="section product-detail">
      <div className="gallery">
        <Image
          className="gallery-main"
          priority
          sizes="(max-width: 700px) 90vw, 50vw"
          src={p.images[image]?.url || "/uyaras-logo.svg"}
          alt={p.images[image]?.alt || p.name}
          width={900}
          height={1000}
        />
        <div className="thumbnails">
          {p.images.map((im, i) => (
            <button
              key={im.id}
              onClick={() => setImage(i)}
              aria-label={"View " + im.alt}
              aria-pressed={i === image}
            >
              <Image src={im.url} alt="" width={90} height={100} />
            </button>
          ))}
        </div>
      </div>
      <div className="product-info">
        <p className="eyebrow">
          <Link href="/products">THE COLLECTION</Link> /{" "}
          {p.category.toUpperCase()}
        </p>
        <h1>{p.name}</h1>
        <p className="price">{money(v?.price ?? p.price)} {v?.regular_price && v.regular_price > v.price ? <del className="muted">{money(v.regular_price)}</del> : null}</p>
        <p className="muted">Sample price, inclusive of provisional tax.</p>
        <p>{p.description}</p>
        {p.fabric && <p>Fabric: {p.fabric}</p>}
        {!p.cod_allowed && <p>Prepaid payment only for this product.</p>}
        <fieldset>
          <legend>Colour — {colour}</legend>
          <div className="choices">
            {[...new Set(p.variants.map((v) => v.colour))].map((c) => (
              <button
                key={c}
                aria-pressed={c === colour}
                onClick={() => {
                  setColour(c);
                  setImage(Math.max(0, p.images.findIndex(im => im.alt.toLowerCase().includes(c.toLowerCase()))));
                }}
              >
                {c}
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>Select your size</legend>
          <div className="choices">
            {[...new Set(p.variants.map((v) => v.size))].map((s) => (
              <button
                key={s}
                disabled={!p.variants.some(v => v.colour === colour && v.size === s && v.active && v.available > 0)}
                aria-pressed={s === size}
                onClick={() => setSize(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </fieldset>
        <p className="muted">
          {v
            ? v.available > 0
              ? `${v.available} units available in the test environment`
              : "No stock entered yet — preview this piece in your bag."
            : "Choose a size to check availability."}
        </p>
        <Button size="lg" className="w-full" disabled={busy || !ready || !v || v.available < 1} onClick={add}>
          {busy ? "Adding…" : "Add to bag"}
        </Button>
        <p role="status">
          {message}{" "}
          {message.startsWith("Added") && <Link href="/cart">View bag →</Link>}
        </p>
        <div className="pin-check">
          <label htmlFor="pin">Check delivery PIN</label>
          <div>
            <input
              id="pin"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              inputMode="numeric"
              maxLength={6}
              placeholder="6-digit PIN"
            />
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const r = await api<{
                    available: boolean;
                    rule: null | { days: string };
                  }>("/checkout/serviceability/" + pin);
                  setDelivery(
                    r.available
                      ? "Test coverage only: " + r.rule?.days
                      : "Coverage not confirmed for this PIN.",
                  );
                } catch (e) {
                  setDelivery((e as Error).message);
                }
              }}
            >
              Check
            </Button>
          </div>
          <p role="status">{delivery}</p>
        </div>
        <details>
          <summary>Size guide</summary>
          <p>{p.size_guide}</p>
        </details>
        <details>
          <summary>Care for your everyday</summary>
          <p>{p.care}</p>
        </details>
        <details>
          <summary>Delivery & returns</summary>
          <p>
            Launch policies are still being prepared.{" "}
            <Link href="/policies/returns">Read the preview policies.</Link>
          </p>
        </details>
      </div>
    </section>
  );
}

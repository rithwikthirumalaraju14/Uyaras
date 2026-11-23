import { serverAll } from "@/lib/server-api";
import Link from "next/link";
import { money } from "@/lib/types";
export const metadata = { title: "Offers" };
export default async function Offers() {
  const items = await serverAll<{ code: string; percent: number; minimum: number; end: number }>("/offers");
  return (
    <section className="section narrow">
      <p className="eyebrow">A LITTLE SOMETHING EXTRA</p>
      <h1>Good things, with a little less.</h1>
      <p className="notice">
        Preview promotions for test checkout. One coupon per order; discounts do
        not stack. Eligibility is verified at checkout.
      </p>
      {items.map((p) => (
        <article className="summary-box" key={p.code}>
          <h2>{p.percent}% off eligible pieces</h2>
          <p>
            Use <strong>{p.code}</strong> on orders from {money(p.minimum)}.
          </p>
          {p.end > 0 && (
            <p>Ends {new Date(p.end * 1000).toLocaleDateString("en-IN")}</p>
          )}
          <Link href="/products">Explore the collection →</Link>
        </article>
      ))}
    </section>
  );
}

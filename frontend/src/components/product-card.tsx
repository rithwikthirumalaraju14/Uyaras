import Image from "next/image";
import Link from "next/link";
import { Product, money } from "@/lib/types";
export function ProductCard({ product: p }: { product: Product }) {
  const cheapest = p.variants.find(v => v.active && v.price === p.price);
  return (
    <article className="product-card">
      <Link href={"/products/" + p.slug} className="product-image">
        <Image
          src={p.images[0]?.url || "/uyaras-logo.svg"}
          alt={p.images[0]?.alt || p.name}
          loading="lazy"
          sizes="(max-width: 700px) 50vw, 25vw"
          width={700}
          height={800}
        />
        <span className="product-badge">Sample collection</span>
        <span className="quick-view">Find your fit ↗</span>
      </Link>
      <div className="product-label">
        <div>
          <p className="eyebrow">{p.category} / everyday essentials</p>
          <Link href={"/products/" + p.slug}>
            <h3>{p.name}</h3>
          </Link>
          <p className="muted">
            {[...new Set(p.variants.map((v) => v.colour))].join(" · ")}
          </p>
        </div>
        <span>{money(p.price)}{cheapest?.regular_price && cheapest.regular_price > p.price ? <><br/><del className="muted">{money(cheapest.regular_price)}</del></> : null}</span>
      </div>
    </article>
  );
}

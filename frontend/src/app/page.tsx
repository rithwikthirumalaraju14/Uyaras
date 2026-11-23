import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight, Wind, Layers, Heart } from "lucide-react";
import { serverApi } from "@/lib/server-api";
import { Product, Storefront } from "@/lib/types";
import { ProductCard } from "@/components/product-card";
export default async function Home() {
  const [catalog, store] = await Promise.all([
    serverApi<{ items: Product[] }>("/products"),
    serverApi<Storefront>("/storefront"),
  ]);
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">UYARAS / CHAPTER 01</p>
          <h1>{store.hero_title}</h1>
          <p>{store.hero_text}</p>
          <Link className="pill-button" href="/products">
            Explore the collection <ArrowUpRight size={18} />
          </Link>
          <span className="hero-footnote">THE EVERYDAY EDIT — MEN & WOMEN</span>
        </div>
        <div className="hero-art">
          <span className="hero-orbit" />
          <Image
            src="/art/M02-atlantic.webp"
            alt="Atlantic blue oversized T-shirt, sample design"
            width={800}
            height={850}
            priority
          />
          <span className="art-note">a feeling, in blue.</span>
          <span className="edition">01 / THE QUIET COLLECTION</span>
        </div>
      </section>
      <div className="marquee">
        SLOW MORNINGS <span>✳</span> EASY LAYERS <span>✳</span> EVERYDAY YOU{" "}
        <span>✳</span> A LITTLE BLUE <span>✳</span> UYARAS
      </div>
      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">GOOD DAYS START SIMPLE</p>
            <h2>Your new everyday.</h2>
          </div>
          <Link href="/products">
            View all pieces <ArrowUpRight size={18} />
          </Link>
        </div>
        <div className="product-grid">
          {catalog.items.slice(0, 4).map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </section>
      <section className="editorial">
        <div>
          <p className="eyebrow">LESS NOISE. MORE YOU.</p>
          <h2>
            Some things just
            <br />
            <em>feel like you.</em>
          </h2>
          <p>
            A favourite tee. A familiar song. The colour of a clear evening.
            Uyaras is our little space for the things that make everyday feel
            good.
          </p>
          <Link href="/products?collection=everyday">
            Meet the everyday edit ↗
          </Link>
        </div>
        <Image
          src="/art/W01-ink.webp"
          alt="Ink blue women's boxy pocket T-shirt, sample design"
          width={800}
          height={800}
          loading="lazy"
          sizes="(max-width: 700px) 50vw, 25vw"
        />
      </section>
      <section className="values">
        <div>
          <Wind />
          <h3>Room to be yourself</h3>
          <p>Relaxed silhouettes and quiet colours.</p>
        </div>
        <div>
          <Layers />
          <h3>Keep it simple</h3>
          <p>A considered beginning: everyday T-shirts.</p>
        </div>
        <div>
          <Heart />
          <h3>Made personal</h3>
          <p>A small brand, taking shape with care.</p>
        </div>
      </section>
    </>
  );
}

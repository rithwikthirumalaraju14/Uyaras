"use client";
import Link from "next/link";
import { useStore } from "./store-provider";
import { ShoppingBag, UserRound, Waves } from "lucide-react";
export function Header({
  categories,
  brand,
}: {
  categories: { id: string; name: string; slug: string }[];
  brand: string;
}) {
  const { auth } = useStore();
  return (
    <>
      <div className="preview-banner">
        UYARAS PREVIEW · Sample products & prices · No real purchases or
        dispatch
      </div>
      <header className="site-header">
        <Link href="/" className="wordmark" aria-label="Uyaras home">
          <Waves size={26} strokeWidth={1.5} />
          {brand.toLowerCase()}
          <span>✳</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/products">Shop all</Link>
          {categories.map((c) => (
            <Link key={c.id} href={"/products?category=" + c.slug}>
              {c.name}
            </Link>
          ))}
          <Link href="/products?collection=new">New arrivals</Link>
          <Link href="/products?sort=popular">Best sellers</Link>
          <Link href="/offers">Offers</Link>
        </nav>
        <div className="header-actions">
          {auth?.user && auth.user.role !== "Customer" && (
            <Link href="/admin">Studio</Link>
          )}
          <Link href="/account" aria-label="My account">
            <UserRound size={21} />
          </Link>
          <Link href="/cart" aria-label="Shopping bag">
            <ShoppingBag size={21} />
          </Link>
        </div>
      </header>
    </>
  );
}

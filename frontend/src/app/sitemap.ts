import type { MetadataRoute } from "next";
import { serverAll } from "@/lib/server-api";
import { Product } from "@/lib/types";
export const dynamic = "force-dynamic";
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = process.env.PUBLIC_ORIGIN || "http://localhost:3000";
  const [items, categories, collections] = await Promise.all([
    serverAll<Product>("/products"), serverAll<{slug:string}>("/categories"), serverAll<{slug:string}>("/collections")
  ]);
  return ["", "/products", "/offers", ...items.map(p=>"/products/"+p.slug),
    ...categories.map(c=>"/products?category="+encodeURIComponent(c.slug)),
    ...collections.map(c=>"/products?collection="+encodeURIComponent(c.slug)),
    ...["shipping","returns","refunds","privacy","terms","contact"].map(p=>"/policies/"+p)
  ].map(path=>({url:origin+path}));
}

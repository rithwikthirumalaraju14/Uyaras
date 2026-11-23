import { serverApi } from "@/lib/server-api";
import { Product } from "@/lib/types";
import { ProductDetail } from "@/components/product-detail";
import { notFound } from "next/navigation";
async function getProduct(slug: string) {
  try {
    return await serverApi<Product>("/products/" + encodeURIComponent(slug));
  } catch {
    return notFound();
  }
}
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const p = await getProduct((await params).slug);
  return {
    title: p.seo_title || p.name,
    description: p.seo_description || p.description,
    alternates: { canonical: "/products/" + p.slug },
  };
}
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const p = await getProduct((await params).slug);
  const structured = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: p.name,
    description: p.description,
    brand: { "@type": "Brand", name: "Uyaras" },
    image: p.images.map((i) =>
      new URL(
        i.url,
        process.env.PUBLIC_ORIGIN || "http://localhost:3000",
      ).toString(),
    ),
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(structured).replace(/</g, "\\u003c"),
        }}
      />
      <ProductDetail product={p} />
    </>
  );
}

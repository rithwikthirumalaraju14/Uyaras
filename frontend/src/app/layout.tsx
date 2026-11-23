import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "./uyaras.css";
import { StoreProvider } from "@/components/store-provider";
import { Header } from "@/components/header";
import { WebVitals } from "@/components/web-vitals";
import { serverApi, serverAll } from "@/lib/server-api";
export const metadata: Metadata = {
  metadataBase: new URL(process.env.PUBLIC_ORIGIN || "http://localhost:3000"),
  title: {
    default: "Uyaras — A softer kind of everyday",
    template: "%s | Uyaras",
  },
  description:
    "Easy T-shirts, quiet colours and everyday comfort. Discover the Uyaras preview collection.",
  robots: {
    index: process.env.INDEX_SITE === "true",
    follow: process.env.INDEX_SITE === "true",
  },
};
export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const categories = await serverAll<{id:string;name:string;slug:string}>("/categories").catch(()=>[]);
  const store = await serverApi<{ brand: string }>("/storefront").catch(() => ({
    brand: "Uyaras",
  }));
  return (
    <html lang="en">
      <body>
        <WebVitals />
        <StoreProvider>
          <a href="#main" className="skip-link" tabIndex={0}>
            Skip to content
          </a>
          <Header categories={categories} brand={store.brand} />
          <main id="main" tabIndex={-1}>{children}</main>
          <footer className="site-footer">
            <div>
              <Link className="wordmark" href="/">
                uyaras
              </Link>
              <p>A softer kind of everyday.</p>
              <small>Designed in blue. Imagined for you.</small>
            </div>
            <div>
              <h2>Explore</h2>
              <Link href="/products">The collection</Link>
              <Link href="/account">Your account</Link>
              <Link href="/orders">Your orders</Link>
            </div>
            <div>
              <h2>Here to help</h2>
              {[
                "shipping",
                "returns",
                "refunds",
                "cancellation",
                "privacy",
                "terms",
                "contact",
              ].map((p) => (
                <Link key={p} href={"/policies/" + p}>
                  {p[0].toUpperCase() + p.slice(1)}
                </Link>
              ))}
            </div>
            <div className="footer-note">
              A brand in the making.
              <br />
              This is a development preview.
              <br />
              No real orders are accepted.
            </div>
          </footer>
        </StoreProvider>
      </body>
    </html>
  );
}

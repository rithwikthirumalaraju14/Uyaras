import { serverApi, serverAll } from "@/lib/server-api";
import Link from "next/link";
import { Product } from "@/lib/types";
import { ProductCard } from "@/components/product-card";
export async function generateMetadata({searchParams}:{searchParams:Promise<Record<string,string|undefined>>}) {
  const params = await searchParams;
  const kind = params.collection ? "collection" : params.category ? "category" : "";
  const rows = kind ? await serverAll<{name:string;slug:string}>(kind === "collection" ? "/collections" : "/categories") : [];
  const selected = rows.find(row => row.slug === params[kind]);
  return {title:selected?.name || "The collection", description:selected ? `Explore ${selected.name} at Uyaras.` : "Explore everyday Uyaras T-shirts.",
    alternates:{canonical: "/products"+(selected ? "?"+kind+"="+encodeURIComponent(selected.slug) : "")},
    ...(params.q ? {robots:{index:false,follow:true}} : {})};
}
export default async function Products({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams(
    Object.entries(params).filter((e): e is [string, string] => !!e[1]),
  );
  if (params.max_rupees)
    query.set("max_price", String(Math.round(Number(params.max_rupees) * 100)));
  const result = await serverApi<{ items: Product[]; total: number; page:number; pages:number }>(
    "/products?" + query,
  );
  const [categories, collections, facets] = await Promise.all([
    serverAll<{name:string;slug:string}>("/categories"),
    serverAll<{name:string;slug:string}>("/collections"),
    serverApi<{sizes:string[];colours:string[]}>("/catalog/facets")
  ]);
  const selectedCategory = categories.find(c => c.slug === params.category);
  const selectedCollection = collections.find(c => c.slug === params.collection);
  function pageUrl(page:number) { const next = new URLSearchParams(query); next.set("page", String(page)); return "/products?"+next; }
  return (
    <section className="section catalog">
      <p className="eyebrow">THE UYARAS EDIT</p>
      <h1>
        {selectedCollection?.name || selectedCategory?.name || "Good things. Easy fits."}
      </h1>
      <p className="muted">
        Thoughtful basics for wherever the day takes you. Sample collection and
        prices.
      </p>
      <form className="filters" action="/products">
        <label>
          Search
          <input
            name="q"
            placeholder="Find your everyday tee"
            defaultValue={params.q}
          />
        </label>
        <label>
          Category
          <select name="category" defaultValue={params.category || ""}>
            <option value="">All pieces</option>
            {categories.map(c => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </select>
        </label>
        <label>Collection<select name="collection" defaultValue={params.collection || ""}><option value="">All collections</option>{collections.map(c=><option key={c.slug} value={c.slug}>{c.name}</option>)}</select></label>
        <label>
          Size
          <select name="size" defaultValue={params.size || ""}>
            <option value="">All sizes</option>
            {facets.sizes.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Colour
          <select name="colour" defaultValue={params.colour || ""}><option value="">All colours</option>{facets.colours.map(c=><option key={c}>{c}</option>)}</select>
        </label>
        <label>
          Max price (₹)
          <input
            name="max_rupees"
            type="number"
            min="0"
            placeholder="e.g. 699"
            defaultValue={params.max_rupees}
          />
        </label>
        <label>
          Sort
          <select name="sort" defaultValue={params.sort || "newest"}>
            <option value="newest">Newest</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
            <option value="popular">Popularity</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            name="available"
            value="true"
            defaultChecked={params.available === "true"}
          />
          Available only
        </label>
        <button className="pill-button" type="submit">
          Apply filters
        </button>
      </form>
      <p className="result-count">{result.total} pieces to make your own</p>
      <div className="product-grid">
        {result.items.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      {result.pages > 1 && <nav aria-label="Product pages" className="choices">
        {result.page > 1 && <Link className="pill-button" href={pageUrl(result.page-1)}>Previous</Link>}
        <span>Page {result.page} of {result.pages}</span>
        {result.page < result.pages && <Link className="pill-button" href={pageUrl(result.page+1)}>Next</Link>}
      </nav>}
      {!result.items.length && (
        <div className="empty">
          No pieces match these filters. Try another colour or size.
        </div>
      )}
    </section>
  );
}

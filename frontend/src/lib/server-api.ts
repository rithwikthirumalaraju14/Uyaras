import "server-only";
export async function serverApi<T>(path: string): Promise<T> {
  const metadata = path.startsWith("/categories") || path.startsWith("/collections");
  const ttl = metadata ? Math.max(0, Number(process.env.CATALOG_METADATA_TTL || "0")) : 0;
  const r = await fetch(
    `${process.env.BACKEND_URL || "http://127.0.0.1:8001"}/api/v1${path}`,
    ttl > 0 ? { next: { revalidate: ttl } } : { cache: "no-store" },
  );
  if (!r.ok) throw new Error(`Store API unavailable (${r.status})`);
  return r.json();
}

export async function serverAll<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  while (true) {
    const result = await serverApi<{items:T[];pages:number}>(`${path}${path.includes("?") ? "&" : "?"}page=${page}&page_size=100`);
    items.push(...result.items);
    if (page >= result.pages) return items;
    page += 1;
  }
}

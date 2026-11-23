"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useStore } from "@/components/store-provider";
import { Order, money } from "@/lib/types";
import { Button } from "@/components/ui/button";
export default function Orders() {
  const { api, ready, auth } = useStore();
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (ready && auth?.user)
      api<{ items: Order[]; pages:number }>("/orders?page="+page)
        .then((r) => {setOrders(r.items);setPages(r.pages);setError("");})
        .catch((e) => setError(e.message)).finally(()=>setLoaded(true));
  }, [ready, auth?.user, api, page]);
  return (
    <section className="section">
      <p className="eyebrow">YOUR UYARAS JOURNEY</p>
      <h1>Your orders.</h1>
      <p role="alert">{error}</p>
      {!ready ? <p>Loading account…</p> : !auth?.user ? (
        <Link href="/account">Sign in to view your orders →</Link>
      ) : !loaded ? <p>Loading orders…</p> : !orders.length ? (
        <p>No orders yet. Your next everyday is waiting.</p>
      ) : (
        orders.map((o) => (
          <Link className="order-row" key={o.id} href={"/orders/" + o.id}>
            <div>
              <strong>#{o.id.slice(0, 8)}</strong>
              <p>{o.lines.map((l) => l.name).join(", ")}</p>
            </div>
            <span>{o.status}</span>
            <span>{money(o.totals.total)}</span>
            <span>View →</span>
          </Link>
        ))
      )}
      {pages > 1 && <nav aria-label="Order pages" className="choices"><Button disabled={page===1} onClick={()=>{setLoaded(false);setPage(page-1);}}>Previous</Button><span>Page {page} of {pages}</span><Button disabled={page>=pages} onClick={()=>{setLoaded(false);setPage(page+1);}}>Next</Button></nav>}
    </section>
  );
}

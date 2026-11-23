"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useStore } from "@/components/store-provider";
import { MediaManager } from "@/components/media-manager";
import { Button } from "@/components/ui/button";
import { Product, Order, money } from "@/lib/types";
type Row = Record<string, unknown>;
type Field = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  default?: unknown;
};
const fields: Record<string, Field[]> = {
  categories: [
    { key: "name", label: "Category name" },
    { key: "slug", label: "URL slug" },
    { key: "parent_id", label: "Parent category ID (optional)" },
    { key: "published", label: "Published", type: "checkbox", default: true },
  ],
  collections: [
    { key: "name", label: "Collection name" },
    { key: "slug", label: "URL slug" },
    { key: "published", label: "Published", type: "checkbox", default: true },
    { key: "product_ids", label: "Product IDs (comma-separated)" },
  ],
  products: [
    { key: "name", label: "Product name" },
    { key: "slug", label: "URL slug" },
    { key: "category_id", label: "Category ID" },
    {
      key: "status",
      label: "Visibility",
      options: ["draft", "published", "archived"],
    },
    { key: "description", label: "Description", type: "textarea" },
    { key: "fabric", label: "Fabric details", type: "textarea" },
    { key: "cod_allowed", label: "Allow COD for this product", type: "checkbox", default: true },
    { key: "care", label: "Care instructions", type: "textarea" },
    { key: "size_guide", label: "Size guide", type: "textarea" },
    { key: "seo_title", label: "Search title" },
    { key: "seo_description", label: "Search description", type: "textarea" },
  ],
  variants: [
    { key: "sku", label: "Unique SKU" },
    { key: "product_id", label: "Product ID" },
    { key: "size", label: "Size" },
    { key: "colour", label: "Colour" },
    { key: "price", label: "Price in paise", type: "number", default: 49900 },
    { key: "regular_price", label: "Regular price in paise (optional)", type: "number" },
    { key: "active", label: "Active", type: "checkbox", default: true },
  ],
  inventory: [
    { key: "sku", label: "SKU" },
    {
      key: "delta",
      label: "Stock adjustment (+ or − units)",
      type: "number",
      default: 0,
    },
    { key: "reason", label: "Adjustment reason" },
    {
      key: "low_stock",
      label: "Low-stock threshold",
      type: "number",
      default: 3,
    },
    {
      key: "real_stock",
      label: "These are verified real units",
      type: "checkbox",
      default: false,
    },
  ],
  rules: [
    { key: "pin", label: "Delivery PIN" },
    { key: "name", label: "Coverage label" },
    {
      key: "shipping",
      label: "Shipping fee (paise)",
      type: "number",
      default: 4900,
    },
    {
      key: "free_over",
      label: "Free shipping threshold (paise)",
      type: "number",
      default: 99900,
    },
    { key: "cod", label: "Allow COD", type: "checkbox", default: false },
    { key: "cod_fee", label: "COD fee (paise)", type: "number", default: 3900 },
    {
      key: "cod_max",
      label: "Maximum COD order (paise)",
      type: "number",
      default: 300000,
    },
    {
      key: "days",
      label: "Delivery estimate",
      default: "3–7 working days (test)",
    },
    {
      key: "verified",
      label: "Coverage verified with carrier",
      type: "checkbox",
      default: false,
    },
  ],
  promotions: [
    { key: "code", label: "Promotion code" },
    {
      key: "percent",
      label: "Discount percentage",
      type: "number",
      default: 10,
    },
    {
      key: "minimum",
      label: "Minimum subtotal (paise)",
      type: "number",
      default: 99900,
    },
    {
      key: "limit",
      label: "Maximum redemptions",
      type: "number",
      default: 100,
    },
    { key: "active", label: "Active", type: "checkbox", default: true },
    {
      key: "start",
      label: "Start Unix timestamp (0 = no start)",
      type: "number",
      default: 0,
    },
    {
      key: "end",
      label: "End Unix timestamp (0 = no expiry)",
      type: "number",
      default: 0,
    },
    {
      key: "eligible_products",
      label: "Eligible product IDs (comma-separated; empty = all)",
    },
    {
      key: "eligible_categories",
      label: "Eligible category IDs (comma-separated; empty = all)",
    },
  ],
  staff: [
    { key: "user_id", label: "Existing user ID" },
    {
      key: "role",
      label: "Role",
      options: [
        "Customer",
        "Catalog Manager",
        "Operations Manager",
        "Support Agent",
        "Read-only Analyst",
        "Owner",
        "Administrator",
      ],
    },
    { key: "active", label: "Account active", type: "checkbox", default: true },
  ],
};
const settingLabels: Record<string, string> = {
  brand: "Brand name",
  announcement: "Announcement",
  hero_title: "Home heading",
  hero_text: "Home introduction",
  support_email: "Support email",
  warehouse: "Warehouse and dispatch details",
  return_days: "Return request window (days)",
  returns_policy: "Returns & exchanges policy",
  shipping_policy: "Shipping policy",
  cancellation_policy: "Cancellation policy",
  privacy_policy: "Privacy policy",
  terms: "Terms",
  tax_bps: "Inclusive demo tax (basis points)",
  tax_confirmed: "Tax verified for production",
  policies_confirmed: "Policies approved",
  inventory_confirmed: "Real inventory verified",
  ordering_enabled: "Production ordering (locked)",
};
export default function Admin() {
  const { auth, ready, api } = useStore();
  const [tab, setTab] = useState("dashboard");
  const [data, setData] = useState<Row>({});
  const [edit, setEdit] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const tabs = [
    "dashboard",
    "products",
    "categories",
    "collections",
    "variants",
    "inventory",
    "orders",
    "shipments",
    "payments",
    "webhooks",
    "reservations",
    "returns",
    "refunds",
    "cod",
    "promotions",
    "rules",
    "customers",
    "staff",
    "settings",
    "movements",
    "audit",
    "outbox",
  ];
  const load = useCallback(
    async (resource = tab) => {
      try {
        setError("");
        setData(await api<Row>("/admin/" + resource + "?page=" + page + "&q=" + encodeURIComponent(search) + "&status=" + encodeURIComponent(statusFilter) + "&customer_id=" + encodeURIComponent(customerFilter)));
      } catch (e) {
        setError((e as Error).message);
        setData({});
      }
    },
    [api, tab, page, search, statusFilter, customerFilter],
  );
  useEffect(() => {
    if (ready && auth?.user && auth.user.role !== "Customer")
      Promise.resolve().then(() => load());
  }, [ready, auth?.user, load]);
  if (!ready) return <section className="section">Loading studio…</section>;
  if (!auth?.user || auth.user.role === "Customer")
    return (
      <section className="section narrow">
        <h1>Uyaras studio.</h1>
        <p>Sign in with a staff account to manage the store.</p>
        <Link href="/account">Sign in →</Link>
      </section>
    );
  const allRows = (data.items || []) as Row[];
  const rows = allRows;
  let formFields = fields[tab];
  if (tab === "settings")
    formFields = Object.entries(data).map(([key, value]) => ({
      key,
      label: settingLabels[key] || key,
      type:
        typeof value === "boolean"
          ? "checkbox"
          : typeof value === "number"
            ? "number"
            : key.includes("policy") || key === "terms"
              ? "textarea"
              : "text",
      default: value,
    }));
  async function save(form: HTMLFormElement) {
    setBusy(true);
    try {
      const values = new FormData(form);
      const body: Row = {};
      for (const field of formFields || [])
        body[field.key] =
          field.type === "checkbox"
            ? values.has(field.key)
            : field.type === "number"
              ? Number(values.get(field.key))
              : String(values.get(field.key) || "");
      if (tab === "variants" && !values.get("regular_price")) body.regular_price = null;
      if (tab === "categories" && !body.parent_id) body.parent_id = null;
      if (tab === "promotions") {
        for (const k of ["eligible_products", "eligible_categories"])
          body[k] = String(body[k])
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
      }
      if (tab === "collections")
        body.product_ids = String(body.product_ids)
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      if (edit?.id && ["categories", "products", "collections"].includes(tab))
        body.id = edit.id;
      await api("/admin/" + tab, body);
      setMessage("Saved.");
      setEdit(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="studio">
      <aside className="studio-nav">
        <p className="eyebrow">UYARAS STUDIO</p>
        <p>
          {auth.user.name}
          <br />
          <small>{auth.user.role}</small>
        </p>
        {tabs.map((t) => (
          <button
            key={t}
            aria-current={tab === t ? "page" : undefined}
            onClick={() => {
              setTab(t);
              setPage(1);
              setSearch("");
              setStatusFilter("");
              setCustomerFilter("");
              setEdit(null);
              setMessage("");
            }}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </aside>
      <div className="studio-body">
        <div className="section-heading">
          <h1>{tab[0].toUpperCase() + tab.slice(1)}</h1>
          <Button variant="outline" onClick={() => void load()}>
            Refresh
          </Button>
        </div>
        <div className="notice">
          Preview operations. Payments, shipment references and stock are test
          data. Production ordering is locked.
        </div>
        <p role="alert">{error}</p>
        <p role="status">{message}</p>
        {Array.isArray(data.items) && (
          <div className="filters">
            <label>
              Search all records
              <input
                value={search}
                onChange={(e) => {setSearch(e.target.value);setPage(1);}}
                placeholder="Name, order, status, email or SKU"
              />
            </label>
            {tab === "orders" && <><label>Order status<select value={statusFilter} onChange={e=>{setStatusFilter(e.target.value);setPage(1);}}><option value="">All statuses</option>{["Pending payment","Confirmed","Processing","Packed","Shipped","Delivered","Cancellation Requested","Cancelled"].map(status=><option key={status}>{status}</option>)}</select></label><label>Customer ID<input value={customerFilter} onChange={e=>{setCustomerFilter(e.target.value);setPage(1);}}/></label></>}
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous page
            </Button>
            <span>Page {page} of {String(data.pages || 1)} ? {String(data.total || 0)} records</span>
            <Button
              variant="outline"
              disabled={
                page >= Number(data.pages || 0)
              }
              onClick={() => setPage(page + 1)}
            >
              Next page
            </Button>
          </div>
        )}
        {tab === "dashboard" ? (
          <div className="metrics">
            {Object.entries(data)
              .filter(([, v]) => typeof v === "number")
              .map(([k, v]) => (
                <article key={k}>
                  <p>{k.replaceAll("_", " ")}</p>
                  <strong>
                    {k === "sales" ? money(Number(v)) : String(v)}
                  </strong>
                </article>
              ))}
          </div>
        ) : tab === "orders" ? (
          rows.map((r) => (
            <StaffOrder
              key={String(r.id)}
              order={r as unknown as Order}
              onDone={() => void load()}
              onError={setError}
            />
          ))
        ) : tab === "returns" ? (
          rows.map((r) => (
            <article className="admin-card" key={String(r.id)}>
              <h2>
                {String(r.kind)} #{String(r.id).slice(0, 8)}
              </h2>
              <p>
                Order: {String(r.order_id)} · Quantity: {String(r.quantity)} ·{" "}
                {String(r.status)}
              </p>
              <p>{String(r.reason)}</p>
              <form
                className="form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  try {
                    await api("/admin/returns/" + r.id, {
                      action: f.get("action"),
                      restock: f.has("restock"),
                      reference: f.get("reference"),
                      condition: f.get("condition"),
                    });
                    await load();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                <label>
                  Action
                  <select name="action">
                    {["approve", "reject", "pickup", "receive", "close"].map(
                      (a) => (
                        <option key={a}>{a}</option>
                      ),
                    )}
                  </select>
                </label>
                <label className="check">
                  <input type="checkbox" name="restock" />
                  Inspected and suitable for restocking
                </label>
                <label>
                  Inspection condition
                  <input name="condition" />
                </label>
                <label>
                  Pickup / refund / replacement reference
                  <input name="reference" />
                </label>
                <Button type="submit">Update return</Button>
              </form>
            </article>
          ))
        ) : (
          tab !== "settings" && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {(rows[0]
                      ? Object.keys(rows[0]).filter(
                          (k) =>
                            ![
                              "variants",
                              "images",
                              "description",
                              "care",
                              "size_guide",
                              "seo_description",
                            ].includes(k),
                        )
                      : []
                    ).map((k) => (
                      <th key={k}>{k.replaceAll("_", " ")}</th>
                    ))}
                    {formFields && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={String(r.id || r.sku || r.code || r.pin || i)}>
                      {Object.entries(r)
                        .filter(
                          ([k]) =>
                            ![
                              "variants",
                              "images",
                              "description",
                              "care",
                              "size_guide",
                              "seo_description",
                            ].includes(k),
                        )
                        .map(([k, v]) => (
                          <td key={k}>
                            {typeof v === "object"
                              ? JSON.stringify(v)
                              : String(v)}
                          </td>
                        ))}
                      {formFields && (
                        <td>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              setEdit(
                                tab === "staff" ? { ...r, user_id: r.id } : r,
                              )
                            }
                          >
                            Edit
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!rows.length && <p>No records yet.</p>}
            </div>
          )
        )}
        {formFields && (
          <form
            key={
              tab +
              String(edit?.id || edit?.sku || edit?.pin || edit?.code || "new")
            }
            className="form admin-form"
            onSubmit={(e) => {
              e.preventDefault();
              void save(e.currentTarget);
            }}
          >
            <h2>
              {tab === "settings"
                ? "Store configuration"
                : edit
                  ? "Edit record"
                  : "Add / update record"}
            </h2>
            <div className="form-grid">
              {formFields.map((f) => (
                <label
                  key={f.key}
                  className={f.type === "checkbox" ? "check" : ""}
                >
                  {f.type === "checkbox" ? (
                    <>
                      <input
                        name={f.key}
                        type="checkbox"
                        defaultChecked={Boolean(edit?.[f.key] ?? f.default)}
                        disabled={f.key === "ordering_enabled"}
                      />
                      {f.label}
                    </>
                  ) : (
                    <>
                      {f.label}
                      {f.options ? (
                        <select
                          name={f.key}
                          defaultValue={String(
                            edit?.[f.key] ?? f.default ?? f.options[0],
                          )}
                        >
                          {f.options.map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      ) : f.type === "textarea" ? (
                        <textarea
                          name={f.key}
                          defaultValue={String(
                            edit?.[f.key] ?? f.default ?? "",
                          )}
                        />
                      ) : (
                        <input
                          name={f.key}
                          type={f.type || "text"}
                          defaultValue={String(
                            edit?.[f.key] ?? f.default ?? "",
                          )}
                        />
                      )}
                    </>
                  )}
                </label>
              ))}
            </div>
            <div className="tabs">
              <Button type="submit" disabled={busy}>
                {busy ? "Saving…" : "Save changes"}
              </Button>
              {edit && (
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => setEdit(null)}
                >
                  Clear form
                </Button>
              )}
            </div>
          </form>
        )}
        {tab === "products" && (
          <MediaManager
            products={rows as unknown as Product[]}
            onDone={() => void load()}
          />
        )}
        {tab === "products" && (
          <MediaUpload
            products={rows as unknown as Product[]}
            onDone={() => void load()}
          />
        )}
      </div>
    </section>
  );
}
function StaffOrder({
  order: o,
  onDone,
  onError,
}: {
  order: Order;
  onDone: () => void;
  onError: (s: string) => void;
}) {
  const { api } = useStore();
  return (
    <article className="admin-card">
      <h2>
        #{o.id.slice(0, 8)} · {o.status}
      </h2>
      <p>
        {o.payment} · {money(o.totals.total)} · {o.address.name}
      </p>
      <p>
        {o.address.line}, {o.address.city}, {o.address.pin}
      </p>
      <p>
        {o.lines
          .map((l) => `${l.name} / ${l.size} × ${l.quantity}`)
          .join(" · ")}
      </p>
      <form
        className="form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          try {
            await api("/admin/orders/" + o.id, {
              action: f.get("action"),
              reference: f.get("reference"),
              carrier: f.get("carrier") || "Manual",
              amount: Number(f.get("amount") || 0),
              reason: f.get("reason"),
              restock: f.has("restock"),
              shipment_status: f.get("shipment_status") || null,
            });
            onDone();
          } catch (e) {
            onError((e as Error).message);
          }
        }}
      >
        <div className="form-grid">
          <label>
            Action
            <select name="action">
              {[
                "process",
                "pack",
                "ship",
                "deliver",
                "cancel",
                      "reject_cancel",
                "rto",
                "rto_receive",
                "cod_collect",
                "cod_remit",
                "refund",
                "tracking",
              ].map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </label>
          <label>
            Tracking / refund / remittance reference
            <input name="reference" />
          </label>
          <label>
            Carrier
            <input name="carrier" defaultValue="Manual" />
          </label>
          <label>
            Amount (paise)
            <input
              name="amount"
              type="number"
              min="0"
              defaultValue={o.totals.total}
            />
          </label>
          <label>
            Reason
            <input name="reason" />
          </label>
          <label>
            Tracking status
            <select name="shipment_status">
              <option value="">Choose for tracking action</option>
              {[
                "Picked up",
                "In transit",
                "Out for delivery",
                "Delivery failed",
                "RTO in transit",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="check">
            <input name="restock" type="checkbox" />
            Inspected goods can be restocked
          </label>
        </div>
        <Button type="submit">Apply action</Button>
        <small>
          Refund actions record an external transfer; they do not send money.
        </small>
      </form>
    </article>
  );
}
function MediaUpload({
  products,
  onDone,
}: {
  products: Product[];
  onDone: () => void;
}) {
  const { api } = useStore();
  const [message, setMessage] = useState("");
  return (
    <form
      className="form admin-form"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const file = f.get("file") as File;
        try {
          const r = await api<{
            url: string;
            object_key: string;
            content_type: string;
          }>("/admin/media/upload", {
            product_id: f.get("product"),
            filename: file.name,
            content_type: file.type,
            size: file.size,
            alt: f.get("alt"),
          });
          const put = await fetch(r.url, {
            method: "PUT",
            headers: { "Content-Type": r.content_type },
            body: file,
          });
          if (!put.ok)
            throw new Error("Upload failed. Check R2 CORS configuration.");
          await api("/admin/media/confirm", {
            product_id: f.get("product"),
            object_key: r.object_key,
            alt: f.get("alt"),
          });
          setMessage("Image uploaded.");
          onDone();
        } catch (e) {
          setMessage((e as Error).message);
        }
      }}
    >
      <h2>Product image upload</h2>
      <p>
        Requires your R2 credentials and browser CORS configuration. No account
        is created automatically.
      </p>
      <label>
        Product
        <select name="product">
          {products.map((p) => (
            <option value={p.id} key={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Image
        <input
          name="file"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          required
        />
      </label>
      <label>
        Accessible image description
        <input name="alt" required />
      </label>
      <Button type="submit">Upload image</Button>
      <p role="status">{message}</p>
    </form>
  );
}

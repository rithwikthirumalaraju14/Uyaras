"use strict";
const main = document.querySelector("#main");
let session,
  bag,
  currentQuote,
  orderKey,
  adminTab = "orders";
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (v) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(v / 100);
const date = (v) => new Date(v * 1000).toLocaleString();
const values = (f) => Object.fromEntries(new FormData(f));
const field = (name, label, type = "text", value = "", required = true) =>
  `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${required ? "required" : ""}></label>`;
const select = (name, label, items, value = "") =>
  `<label>${label}<select name="${name}" aria-label="${esc(label)}">${items
    .map((x) => {
      const [v, l] = Array.isArray(x) ? x : [x, x];
      return `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(l)}</option>`;
    })
    .join("")}</select></label>`;
function toast(message) {
  const t = document.querySelector("#toast");
  t.textContent = message;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 5000);
}
async function api(path, method = "GET", body, extra = {}) {
  const r = await fetch("/api/v1" + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(session ? { "X-CSRF-Token": session.csrf } : {}),
      ...extra,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const data = await r.json();
  if (!r.ok)
    throw Error(
      data.error?.message ||
        data.detail ||
        "The request could not be completed.",
    );
  return data;
}
function formHandler(id, fn) {
  const f = document.getElementById(id);
  if (!f) return;
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const b =
      f.querySelector("button[type=submit]") || f.querySelector("button");
    const status = f.querySelector(".form-status");
    if (b) b.disabled = true;
    if (status) status.textContent = "";
    try {
      await fn(values(f), f);
    } catch (err) {
      if (status) status.textContent = err.message;
      toast(err.message);
    } finally {
      if (b) b.disabled = false;
    }
  });
}
const status = '<p class="form-status" role="alert"></p>';
const button = (label) => `<button type="submit">${label}</button>${status}`;
async function refreshBag() {
  bag = await api("/cart");
  document.querySelector("#bag-count").textContent = bag.lines.reduce(
    (n, l) => n + l.quantity,
    0,
  );
}
function empty(title, body, link = "/shop", label = "Explore the collection") {
  return `<div class="empty"><h1>${title}</h1><p class="muted">${body}</p><a href="${link}" class="button">${label}</a></div>`;
}
function card(p) {
  return `<article class="product-card"><a href="/products/${esc(p.slug)}"><div class="image">${p.images[0] ? `<img src="${esc(p.images[0].url)}" alt="${esc(p.images[0].alt)}" loading="lazy">` : ""}</div><div class="card-meta"><h3>${esc(p.name)}</h3></div><div class="card-meta"><small>${esc(p.category)} · ${new Set(p.variants.map((v) => v.colour)).size} colours</small><span>${money(p.price)}</span></div></a></article>`;
}
async function shop(home = false) {
  const query = new URLSearchParams(location.search);
  const [res, cats, colls] = await Promise.all([
    api("/products?" + query),
    api("/categories"),
    api("/collections"),
  ]);
  main.innerHTML =
    (home
      ? `<section class="hero"><div class="hero-copy"><div class="eyebrow">A little less ordinary</div><h1>Your everyday.<br>Better dressed.</h1><p>Easy silhouettes. Considered colours. Discover the pieces you'll reach for again and again.</p><a href="/shop" class="button">Find your everyday ↗</a></div><div class="hero-image"><img src="/art/M01-pine.webp" alt="Everyday crew T-shirt in pine green"><div class="image-caption">THE EVERYDAY EDIT &nbsp; / &nbsp; 01</div></div></section><div class="trust"><span>THOUGHTFUL EVERYDAY STYLES</span><span>FIND YOUR FIT</span><span>DELIVERY TO SELECT PIN CODES</span></div>`
      : "") +
    `<div class="wrap"><div class="section-title"><div><p class="eyebrow">${home ? "The essentials" : "Find something that feels like you"}</p><h${home ? "2" : "1"}>${home ? "On repeat. For a reason." : "The everyday collection"}</h${home ? "2" : "1"}></div><span class="muted">${res.total} styles</span></div>${
      !home
        ? `<form id="filters" class="filters">${field("q", "Search styles", "search", query.get("q") || "", false)}${select("category", "Category", [["", "All categories"], ...cats.items.map((c) => [c.id, c.name])], query.get("category") || "")}${select("collection", "Collection", [["", "All collections"], ...colls.items.map((c) => [c.id, c.name])], query.get("collection") || "")}${select("size", "Size", [["", "All sizes"], "S", "M", "L", "XL"], query.get("size") || "")}${select(
            "sort",
            "Sort",
            [
              ["newest", "Newest"],
              ["price-asc", "Price: low to high"],
              ["price-desc", "Price: high to low"],
            ],
            query.get("sort") || "newest",
          )}<button>Apply filters</button>${field("colour", "Colour", "text", query.get("colour") || "", false)}${field("max_price", "Maximum price (?)", "number", query.get("max_price") ? Number(query.get("max_price")) / 100 : "", false)}<label class="check"><input type="checkbox" name="available" value="true" ${query.get("available") ? "checked" : ""}> In stock only</label></form>`
        : ""
    }<div class="grid">${res.items.map(card).join("")}</div>${!res.items.length ? empty("Nothing here just yet.", "Try another search or clear your filters.") : ""}${res.total > 24 ? `<div class="row"><a href="?${esc(new URLSearchParams({ ...Object.fromEntries(query), page: Math.max(1, Number(query.get("page") || 1) - 1) }))}">Previous</a><a href="?${esc(new URLSearchParams({ ...Object.fromEntries(query), page: Number(query.get("page") || 1) + 1 }))}">Next</a></div>` : ""}</div>`;
  formHandler("filters", (d) => {
    if (d.max_price) d.max_price = Math.round(Number(d.max_price) * 100);
    Object.keys(d).forEach((k) => {
      if (!d[k]) delete d[k];
    });
    location.href = "/shop?" + new URLSearchParams(d);
  });
}
async function product() {
  const p = await api("/products/" + location.pathname.split("/").pop());
  main.innerHTML = `<div class="wrap"><p class="muted"><a href="/shop">Shop</a> / ${esc(p.name)}</p><div class="split"><div><img class="product-image" id="product-image" src="${esc(p.images[0]?.url || "")}" alt="${esc(p.images[0]?.alt || p.name)}"><div class="thumbs">${p.images.map((im, i) => `<button data-image="${i}" aria-label="View ${esc(im.alt)}"><img src="${esc(im.url)}" alt="${esc(im.alt)}"></button>`).join("")}</div></div><div class="detail"><p class="eyebrow">${esc(p.category)} / Everyday essentials</p><h1>${esc(p.name)}</h1><p class="price">${money(p.price)}</p><p class="muted">${esc(p.description)}</p><form id="add">${select(
    "sku",
    "Choose colour & size",
    p.variants.map((v) => [
      v.sku,
      `${v.colour} / ${v.size} ${v.available && v.active ? "— " + v.available + " available" : "— Sold out"}`,
    ]),
  )}${field("quantity", "Quantity", "number", 1)}${button("Add to bag")}</form><form id="pin"><div class="row">${field("pin", "Check delivery PIN", "text", "")}<button type="submit" class="secondary">Check</button></div><p id="pin-result" role="status"></p></form><details open><summary>Fabric & care</summary><p>${esc(p.care)}</p></details><details><summary>Size guide</summary><p>${esc(p.size_guide)}</p></details><details><summary>Delivery & returns</summary><p>Availability and fees depend on your delivery PIN. <a href="/policies">Read the current policies.</a></p></details></div></div></div>`;
  document.querySelectorAll("[data-image]").forEach(
    (b) =>
      (b.onclick = () => {
        const im = p.images[Number(b.dataset.image)],
          el = document.querySelector("#product-image");
        el.src = im.url;
        el.alt = im.alt;
      }),
  );
  const sku = document.querySelector("[name=sku]");
  [...sku.options].forEach(
    (o, i) =>
      (o.disabled = !p.variants[i].active || p.variants[i].available < 1),
  );
  const first = p.variants.find((v) => v.active && v.available > 0);
  if (first) sku.value = first.sku;
  else document.querySelector("#add button").disabled = true;
  formHandler("add", async (d) => {
    const existing = bag.lines.find((l) => l.sku === d.sku)?.quantity || 0;
    await api("/cart/items", "POST", {
      sku: d.sku,
      quantity: Number(d.quantity) + existing,
    });
    await refreshBag();
    toast("Added to your bag");
  });
  formHandler("pin", async (d) => {
    const r = await api("/checkout/serviceability", "POST", d);
    document.querySelector("#pin-result").textContent = r.serviceable
      ? `${r.rule.days}. Shipping ${money(r.rule.shipping)}. ${r.rule.cod ? "COD available." : "Prepaid only."}`
      : "We do not deliver to this PIN yet.";
  });
}
function totals(q) {
  return `<dl><dt>Subtotal</dt><dd>${money(q.subtotal)}</dd>${q.discount ? `<dt>Discount</dt><dd>−${money(q.discount)}</dd>` : ""}${q.shipping !== undefined ? `<dt>Shipping</dt><dd>${money(q.shipping)}</dd><dt>COD fee</dt><dd>${money(q.cod_fee)}</dd><dt>Tax</dt><dd>${money(q.tax)}</dd>` : ""}<dt class="total">Total</dt><dd class="total">${money(q.total ?? q.subtotal)}</dd></dl>`;
}
async function cart() {
  await refreshBag();
  main.innerHTML = bag.lines.length
    ? `<div class="wrap"><p class="eyebrow">Good choices</p><h1>Your bag.</h1><div class="checkout"><section>${bag.lines.map((l) => `<div class="cart-line"><img src="${esc(l.image)}" alt="${esc(l.name)}"><div><h3><a href="/products/${esc(l.slug)}">${esc(l.name)}</a></h3><p class="muted">${esc(l.colour)} / ${esc(l.size)}</p><small>${money(l.price)} each</small></div><label>Quantity<input data-qty="${esc(l.sku)}" type="number" min="0" max="99" value="${l.quantity}" aria-label="Quantity for ${esc(l.name)}"></label><button class="secondary" data-remove="${esc(l.sku)}">Remove</button></div>`).join("")}</section><aside class="panel summary"><h2>Order summary</h2>${totals(bag)}<p class="muted">Shipping and any applicable fees are calculated at checkout.</p><a href="/checkout" class="button">Continue to checkout</a></aside></div></div>`
    : empty("Your bag is waiting.", "Find your new everyday favourite.");
  document.querySelectorAll("[data-qty]").forEach(
    (i) =>
      (i.onchange = async () => {
        try {
          await api("/cart/items", "POST", {
            sku: i.dataset.qty,
            quantity: Number(i.value),
          });
          await cart();
        } catch (e) {
          toast(e.message);
          await cart();
        }
      }),
  );
  document.querySelectorAll("[data-remove]").forEach(
    (b) =>
      (b.onclick = async () => {
        try {
          await api("/cart/items", "POST", {
            sku: b.dataset.remove,
            quantity: 0,
          });
          await cart();
        } catch (e) {
          toast(e.message);
        }
      }),
  );
}
const addressForm = () =>
  `<form id="address" class="panel"><h2>Add an address</h2>${field("name", "Recipient name")}${field("phone", "Phone", "tel")}${field("line", "Street address")}<div class="row">${field("city", "City")}${field("state", "State")}</div>${field("pin", "Six-digit PIN")} ${button("Save address")}</form>`;
function bindAddress(after) {
  formHandler("address", async (d) => {
    await api("/addresses", "POST", d);
    toast("Address saved");
    await after();
  });
}
async function account() {
  if (!session.user) {
    main.innerHTML = `<div class="wrap account-grid"><form id="login" class="panel"><p class="eyebrow">Welcome back</p><h1>Make yourself<br>at home.</h1>${field("email", "Email", "email")}${field("password", "Password", "password")}${button("Sign in")}<a href="/reset-password">Forgot password?</a></form><form id="register" class="panel"><h2>A little more you.</h2><p class="muted">Save your addresses and keep track of your orders.</p>${field("name", "Your name")}${field("email", "Email", "email")}${field("password", "Password (at least 12 characters)", "password")}${button("Create account")}</form></div>`;
    for (const action of ["login", "register"])
      formHandler(action, async (d) => {
        const result = await api("/auth/" + action, "POST", d);
        session = { ...session, ...result };
        location.href =
          new URLSearchParams(location.search).get("next") === "/checkout"
            ? "/checkout"
            : "/account";
      });
    return;
  }
  const me = await api("/me");
  main.innerHTML = `<div class="wrap"><div class="section-title"><div><p class="eyebrow">Your account</p><h1>Hello, ${esc(me.user.name)}.</h1><p>${esc(me.user.email)}</p></div><button id="logout" class="secondary">Sign out</button></div><div class="account-grid"><section><h2>Your addresses</h2>${me.addresses.map((a) => `<div class="panel"><strong>${esc(a.name)}</strong><p>${esc(a.line)}, ${esc(a.city)}, ${esc(a.state)} ${esc(a.pin)}<br>${esc(a.phone)}</p><button class="secondary" data-address="${esc(a.id)}">Remove</button></div>`).join("") || "<p>No saved addresses yet.</p>"}<p><a class="button secondary" href="/orders">View your orders</a> ${session.user.role !== "Customer" ? '<a class="button" href="/admin">Open staff workspace</a>' : ""}</p></section>${addressForm()}</div></div>`;
  document.querySelector("#logout").onclick = async () => {
    try {
      await api("/auth/logout", "POST", {});
      location.href = "/";
    } catch (e) {
      toast(e.message);
    }
  };
  document.querySelectorAll("[data-address]").forEach(
    (b) =>
      (b.onclick = async () => {
        try {
          await api("/addresses/" + b.dataset.address, "DELETE");
          await account();
        } catch (e) {
          toast(e.message);
        }
      }),
  );
  bindAddress(account);
  profileForm(me.user);
}
async function reset() {
  main.innerHTML = `<div class="wrap account-grid"><form id="forgot" class="panel"><h1>Forgot your password?</h1><p>Request recovery instructions for your account.</p>${field("email", "Email", "email")}${button("Request recovery")}</form><form id="reset" class="panel"><h2>Set a new password</h2>${field("token", "Recovery token", "text", new URLSearchParams(location.search).get("token") || "")}${field("password", "New password (12+ characters)", "password")}${button("Reset password")}</form></div>`;
  formHandler("forgot", async (d) =>
    toast((await api("/auth/forgot-password", "POST", d)).message),
  );
  formHandler("reset", async (d) => {
    await api("/auth/reset-password", "POST", d);
    location.href = "/account";
  });
}
async function checkout() {
  if (!session.user) {
    location.href = "/account?next=/checkout";
    return;
  }
  await refreshBag();
  if (!bag.lines.length) {
    await cart();
    return;
  }
  const me = await api("/me");
  main.innerHTML = `<div class="wrap"><p class="eyebrow">Almost yours</p><h1>The final details.</h1>${session.sandbox ? '<div class="notice">Local test checkout. No real payment is taken. Seeded test PINs: 500001 (COD/prepaid), 520001 (prepaid).</div>' : ""}<div class="checkout"><section><form id="quote" class="panel"><h2>Delivery & payment</h2>${select(
    "address_id",
    "Delivery address",
    me.addresses.map((a) => [a.id, `${a.name}: ${a.line}, ${a.city} ${a.pin}`]),
  )}${select("method", "Payment method", ["COD", "Prepaid"])}${field("coupon", "Coupon code", "text", "", false)}${button("Review order total")}</form><details ${!me.addresses.length ? "open" : ""}><summary>Add a new delivery address</summary>${addressForm()}</details></section><aside class="panel summary"><h2>Your order</h2>${bag.lines.map((l) => `<p>${esc(l.name)} · ${esc(l.size)} × ${l.quantity}<br><small>${money(l.price * l.quantity)}</small></p>`).join("")}<div id="quote-result">${totals(bag)}<p class="muted">Review the total before placing your order.</p></div></aside></div></div>`;
  currentQuote = null;
  bindAddress(checkout);
  formHandler("quote", async (d) => {
    const address = me.addresses.find((a) => a.id === d.address_id);
    if (!address) throw Error("Save a delivery address first.");
    currentQuote = await api("/checkout/quote", "POST", {
      ...d,
      pin: address.pin,
    });
    orderKey = crypto.randomUUID();
    document.querySelector("#quote-result").innerHTML =
      totals(currentQuote) +
      `<p class="muted">Quote valid for 5 minutes.</p><button id="place">Place ${currentQuote.method === "COD" ? "COD" : "test prepaid"} order</button>`;
    document.querySelector("#place").onclick = async (e) => {
      e.target.disabled = true;
      try {
        const o = await api(
          "/checkout/orders",
          "POST",
          { quote_id: currentQuote.id },
          { "Idempotency-Key": orderKey },
        );
        location.href = "/orders/" + o.id;
      } catch (err) {
        toast(err.message);
        e.target.disabled = false;
      }
    };
  });
  document.querySelector("#quote").addEventListener("change", () => {
    currentQuote = null;
    document.querySelector("#quote-result").innerHTML =
      "<p>Details changed. Review a fresh quote.</p>";
  });
}
function orderCard(o) {
  return `<article class="panel order-card"><div class="row"><div><h3><a href="/orders/${esc(o.id)}">${esc(o.id)}</a></h3><small>${date(o.created)}</small></div><span class="badge">${esc(o.status)}</span><strong>${money(o.total)}</strong></div><p>${o.lines.map((l) => esc(l.name) + " × " + l.quantity).join(", ")}</p><p class="muted">Payment: ${esc(o.payment)} · Shipping: ${esc(o.shipment)}</p><a href="/orders/${esc(o.id)}">View order →</a></article>`;
}
async function orders() {
  if (!session.user) {
    main.innerHTML = empty(
      "Your orders, all together.",
      "Sign in to see your order history.",
      "/account",
      "Sign in",
    );
    return;
  }
  const id = location.pathname.split("/")[2];
  if (!id) {
    const r = await api("/orders");
    main.innerHTML = `<div class="wrap"><p class="eyebrow">Your wardrobe, in the making</p><h1>Your orders.</h1>${r.items.map(orderCard).join("") || empty("No orders yet.", "Your next favourite is waiting.")}</div>`;
    return;
  }
  const o = await api("/orders/" + id);
  main.innerHTML = `<div class="wrap"><p><a href="/orders">← All orders</a></p><div class="section-title"><h1>${esc(o.id)}</h1><span class="badge">${esc(o.status)}</span></div><div class="checkout"><section class="panel"><h2>Order details</h2>${o.lines.map((l) => `<p><strong>${esc(l.name)}</strong> · ${esc(l.colour)} / ${esc(l.size)} × ${l.quantity}<br>${money(l.price * l.quantity)}</p>`).join("")}<h3>Deliver to</h3><p>${esc(o.address.name)}<br>${esc(o.address.line)}, ${esc(o.address.city)} ${esc(o.address.pin)}</p><p>Payment: ${esc(o.payment)}<br>Shipment: ${esc(o.shipment)}<br>Tracking: ${esc(o.tracking || "Available after dispatch")}</p>${o.status === "Pending payment" && session.sandbox ? `<div class="notice"><strong>Sandbox payment</strong><p>Choose an outcome to test the payment flow. No money is charged.</p><div class="row"><button data-pay="success">Test success</button><button class="secondary" data-pay="failed">Test failure</button></div></div>` : ""}${["Payment failed", "Payment expired"].includes(o.status) && o.payment === "Failed" ? '<button id="retry">Retry payment</button>' : ""}${["Pending payment", "Confirmed", "Processing", "Packed"].includes(o.status) ? `<details><summary>Cancel order</summary><form id="cancel">${field("reason", "Cancellation reason")}${button("Cancel order")}</form></details>` : ""}${
    o.status === "Delivered"
      ? `<details><summary>Request a return</summary><form id="return">${select(
          "sku",
          "Item",
          o.lines.map((l) => [l.sku, `${l.name} ${l.size}`]),
        )}${field("quantity", "Quantity", "number", 1)}${field("reason", "Reason")}${button("Submit return request")}</form></details>`
      : ""
  }${o.returns.length ? "<h3>Returns</h3>" + o.returns.map((r) => `<p>${esc(r.sku)} × ${r.quantity}: ${esc(r.status)} · Refund ${money(r.refund)}</p>`).join("") : ""}</section><aside class="panel summary"><h2>Payment summary</h2>${totals(o)}${o.refund ? `<p>Refund recorded: ${money(o.refund)}</p>` : ""}<div class="timeline">${o.timeline.map((t) => `<p>${esc(t.message)}<small>${date(t.at)}</small></p>`).join("")}</div></aside></div></div>`;
  document.querySelectorAll("[data-pay]").forEach(
    (b) =>
      (b.onclick = async () => {
        b.disabled = true;
        try {
          await api("/orders/" + id + "/sandbox-payment", "POST", {
            outcome: b.dataset.pay,
          });
          await orders();
        } catch (e) {
          toast(e.message);
          b.disabled = false;
        }
      }),
  );
  const retry = document.querySelector("#retry");
  if (retry)
    retry.onclick = async () => {
      try {
        await api("/orders/" + id + "/payment-retry", "POST", {});
        await orders();
      } catch (e) {
        toast(e.message);
      }
    };
  formHandler("cancel", async (d) => {
    await api("/orders/" + id + "/cancel", "POST", d);
    await orders();
  });
  formHandler("return", async (d) => {
    await api("/orders/" + id + "/returns", "POST", {
      ...d,
      quantity: Number(d.quantity),
    });
    await orders();
  });
}
function policies() {
  main.innerHTML = `<div class="wrap policy"><p class="eyebrow">Clear expectations</p><h1>A few things to know.</h1><div class="notice">This is a local development store. The following are test settings, not approved trading policies. No real purchases or deliveries are offered.</div><section><h2>Shipping</h2><p>Delivery is limited to configured PIN codes. Checkout shows applicable shipping, COD fees and tax before you place an order. The sample dataset contains test coverage only.</p></section><section><h2>Returns & refunds</h2><p>The local application supports return requests within 14 days of delivery, staff inspection, and manual refund references. This testing rule must be replaced with the approved business policy before launch.</p></section><section id="privacy"><h2>Privacy & terms</h2><p>Account, address and order information is saved in this installation's database. Passwords are hashed. Sandbox payments do not collect card details. Use fictional addresses when testing. Final privacy terms, retention and deletion processes require business approval.</p></section><section id="contact"><h2>Contact</h2><p>The business support email, phone, legal name and address have not been configured. Customer support must be staffed before the store opens.</p></section></div>`;
}
const adminTabs = [
  "orders",
  "products",
  "categories",
  "collections",
  "stock",
  "rules",
  "promotions",
  "customers",
  "staff",
  "audit",
  "outbox",
];
async function admin() {
  if (!session.user || session.user.role === "Customer") {
    main.innerHTML = empty(
      "Staff workspace",
      "Sign in with an account provisioned by the store owner.",
      "/account",
      "Sign in",
    );
    return;
  }
  main.innerHTML = `<div class="wrap"><p class="eyebrow">Store operations · ${esc(session.user.role)}</p><h1>Staff workspace.</h1><div class="tabs">${adminTabs
    .filter(
      (t) => !["staff", "outbox"].includes(t) || session.user.role === "Owner",
    )
    .map(
      (t) =>
        `<button data-tab="${t}" class="secondary ${t === adminTab ? "active" : ""}">${t[0].toUpperCase() + t.slice(1)}</button>`,
    )
    .join(
      "",
    )}</div><section id="admin-content" aria-live="polite">Loading…</section></div>`;
  document.querySelectorAll("[data-tab]").forEach(
    (b) =>
      (b.onclick = () => {
        adminTab = b.dataset.tab;
        admin().catch((e) => toast(e.message));
      }),
  );
  await adminContent();
}
const table = (headers, rows) =>
  `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
function editor(title, fields) {
  return `<form id="admin-edit" class="panel admin-form"><h2>${title}</h2>${fields}${button("Save changes")}</form>`;
}
function jsonField(name, label, value) {
  return `<label>${label}<textarea class="code" name="${name}">${esc(JSON.stringify(value, null, 2))}</textarea></label>`;
}
async function adminContent() {
  const el = document.querySelector("#admin-content");
  const { items } = await api("/admin/" + adminTab);
  const list = Array.isArray(items) ? items : Object.values(items);
  let html = "";
  if (adminTab === "orders") {
    html = table(
      ["Order", "Customer", "Total", "Order / payment / shipment", "Actions"],
      list
        .slice()
        .reverse()
        .map((o) => [
          esc(o.id),
          esc(o.address.name),
          money(o.total),
          `${esc(o.status)}<br>${esc(o.payment)}<br>${esc(o.shipment)}`,
          `<button data-order="${esc(o.id)}">Manage</button>`,
        ]),
    );
  }
  if (adminTab === "products") {
    html =
      table(
        ["Name", "Price", "Status", "Variants", ""],
        list.map((p) => [
          esc(p.name),
          money(p.price),
          esc(p.status),
          p.variants.length,
          `<button data-edit="${esc(p.id)}">Edit</button>`,
        ]),
      ) +
      '<button id="new-product" class="secondary">New product</button><div id="product-editor"></div>';
  }
  if (adminTab === "stock") {
    html =
      table(
        ["SKU", "On hand", "Reserved", "Available"],
        Object.entries(items).map(([sku, b]) => [
          esc(sku),
          b.on_hand,
          b.reserved,
          b.on_hand - b.reserved,
        ]),
      ) +
      editor(
        "Adjust inventory",
        select("sku", "SKU", Object.keys(items)) +
          field("delta", "Quantity adjustment (+ / −)", "number") +
          field("reason", "Reason"),
      );
  }
  if (adminTab === "categories") {
    html =
      table(
        ["ID", "Name", "Parent", "Published"],
        list.map((c) => [
          esc(c.id),
          esc(c.name),
          esc(c.parent_id || "—"),
          c.published ? "Yes" : "No",
        ]),
      ) +
      editor(
        "Create or update category",
        field("id", "Category ID") +
          field("slug", "URL slug") +
          field("name", "Display name") +
          select("parent_id", "Parent", [
            ["", "None"],
            ...list.map((c) => [c.id, c.name]),
          ]) +
          select("published", "Visibility", [
            ["true", "Published"],
            ["false", "Hidden"],
          ]),
      );
  }
  if (adminTab === "collections") {
    const products = await api("/admin/products");
    html =
      table(
        ["ID", "Name", "Products"],
        list.map((c) => [
          esc(c.id),
          esc(c.name),
          esc(c.product_ids.join(", ")),
        ]),
      ) +
      editor(
        "Save collection",
        field("id", "ID (leave blank to create)", "text", "", false) +
          field("name", "Collection name") +
          field("product_ids", "Product IDs, comma separated"),
      ) +
      `<p>Available IDs: ${Object.keys(products.items).map(esc).join(", ")}</p>`;
  }
  if (adminTab === "rules") {
    html =
      table(
        ["PIN", "Area", "Shipping", "COD", "Estimate"],
        list.map((r) => [
          esc(r.pin),
          esc(r.name),
          money(r.shipping),
          r.cod ? "Yes" : "No",
          esc(r.days),
        ]),
      ) +
      editor(
        "Configure delivery PIN",
        field("pin", "PIN") +
          field("name", "Region name") +
          field("days", "Delivery estimate", "text", "", false) +
          select("cod", "COD", [
            ["true", "Enabled"],
            ["false", "Disabled"],
          ]) +
          ["shipping", "cod_fee", "cod_max", "free_over", "tax_bps"]
            .map((k) =>
              field(
                k,
                k === "tax_bps"
                  ? "Tax basis points (500 = 5%; added to price)"
                  : k.replaceAll("_", " ") + " (paise; 0 disables thresholds)",
                "number",
                0,
              ),
            )
            .join("") +
          select("delete", "Action", [
            ["false", "Save rule"],
            ["true", "Disable PIN"],
          ]),
      );
  }
  if (adminTab === "promotions") {
    html =
      table(
        ["Code", "Discount", "Minimum", "Used limit", "Active"],
        list.map((p) => [
          esc(p.code),
          p.percent + "%",
          money(p.minimum),
          p.limit || "Unlimited",
          p.active ? "Yes" : "No",
        ]),
      ) +
      editor(
        "Create or update promotion",
        field("code", "Coupon code") +
          field("percent", "Discount percentage", "number", 10) +
          field("minimum", "Minimum spend (paise)", "number", 0) +
          field("limit", "Usage limit (0 = unlimited)", "number", 0) +
          field(
            "start",
            "Starts (Unix seconds; 0 = immediately)",
            "number",
            0,
          ) +
          field("end", "Ends (Unix seconds; 0 = no expiry)", "number", 0) +
          select("active", "Status", [
            ["true", "Active"],
            ["false", "Disabled"],
          ]),
      );
  }
  if (["customers", "staff"].includes(adminTab)) {
    html = table(
      ["Name", "Email", "Role", "ID"],
      list.map((u) => [esc(u.name), esc(u.email), esc(u.role), esc(u.id)]),
    );
    if (adminTab === "staff")
      html += editor(
        "Assign staff role",
        select(
          "id",
          "Account",
          list.filter((u) => u.role !== "Owner").map((u) => [u.id, u.email]),
        ) +
          select("role", "Role", [
            "Customer",
            "Catalog",
            "Operations",
            "Support",
            "Analyst",
            "Owner",
          ]),
      );
  }
  if (adminTab === "audit") {
    html = table(
      ["When", "Actor", "Action", "Target", "Changes"],
      list
        .slice()
        .reverse()
        .slice(0, 200)
        .map((a) => [
          date(a.at),
          esc(a.actor),
          esc(a.action),
          esc(a.target),
          `<details><summary>Inspect</summary><pre>${esc(JSON.stringify({ before: a.before, after: a.after }, null, 2))}</pre></details>`,
        ]),
    );
  }
  if (adminTab === "outbox") {
    html =
      '<div class="notice">Notifications are queued locally. Use the notification worker with SMTP settings to deliver email. Recovery tokens are never exposed here.</div>' +
      table(
        ["Created", "Kind", "Status", "Message"],
        list
          .slice()
          .reverse()
          .map((n) => [
            date(n.created),
            esc(n.kind || "order"),
            esc(n.status),
            esc(n.message || "Password recovery"),
          ]),
      );
  }
  el.innerHTML = html || "<p>No records yet.</p>";
  formHandler("admin-edit", async (d) => {
    for (const k of [
      "delta",
      "shipping",
      "cod_fee",
      "cod_max",
      "free_over",
      "tax_bps",
      "percent",
      "minimum",
      "limit",
      "start",
      "end",
    ])
      if (k in d) d[k] = Number(d[k]);
    for (const k of ["cod", "active", "published", "delete"])
      if (k in d) d[k] = d[k] === "true";
    if ("product_ids" in d)
      d.product_ids = d.product_ids
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    await api("/admin/" + adminTab, "POST", d);
    toast("Saved");
    await adminContent();
  });
  document
    .querySelectorAll("[data-order]")
    .forEach((b) => (b.onclick = () => adminOrder(items[b.dataset.order])));
  document
    .querySelectorAll("[data-edit]")
    .forEach((b) => (b.onclick = () => productEditor(items[b.dataset.edit])));
  const np = document.querySelector("#new-product");
  if (np) np.onclick = () => productEditor();
}
async function productEditor(p = {}) {
  const cats = await api("/admin/categories");
  document.querySelector("#product-editor").innerHTML = editor(
    p.id ? "Edit product" : "Create product",
    `<input type="hidden" name="id" value="${esc(p.id || "")}">` +
      field("name", "Product name", "text", p.name || "") +
      field("slug", "URL slug", "text", p.slug || "") +
      field("price", "Price in paise", "number", p.price || 39900) +
      select(
        "category",
        "Category",
        Object.values(cats.items).map((c) => [c.id, c.name]),
        p.category,
      ) +
      select(
        "status",
        "Status",
        ["draft", "published", "archived"],
        p.status || "draft",
      ) +
      field("description", "Description", "text", p.description || "", false) +
      field("care", "Care instructions", "text", p.care || "", false) +
      field("size_guide", "Size guide", "text", p.size_guide || "", false) +
      jsonField(
        "variants",
        "Variants (JSON; existing SKUs must be retained)",
        p.variants || [
          { sku: "NEW-BLACK-M", colour: "Black", size: "M", active: true },
        ],
      ) +
      jsonField(
        "images",
        "Image URLs & alternative text (JSON)",
        p.images || [{ url: "/art/M01-pine.webp", alt: "Sample tee" }],
      ),
  );
  formHandler("admin-edit", async (d) => {
    d.price = Number(d.price);
    d.variants = JSON.parse(d.variants);
    d.images = JSON.parse(d.images);
    await api("/admin/products", "POST", d);
    toast("Product saved");
    await adminContent();
  });
  document
    .querySelector("#product-editor")
    .scrollIntoView({ behavior: "smooth" });
}
async function adminOrder(o) {
  const el = document.querySelector("#admin-content");
  el.innerHTML = `<button id="back-admin" class="secondary">← Orders</button><div class="panel"><h2>${esc(o.id)}</h2><p>${esc(o.status)} · ${esc(o.payment)} · ${esc(o.shipment)}</p><p>${esc(o.address.name)}, ${esc(o.address.line)}, ${esc(o.address.city)} ${esc(o.address.pin)} · ${esc(o.address.phone)}</p>${o.lines.map((l) => `<p>${esc(l.sku)} × ${l.quantity} · ${money(l.price * l.quantity)}</p>`).join("")}<p>Total ${money(o.total)} · Collected ${money(o.collected)} · Remitted ${money(o.remitted)} · Refunded ${money(o.refund)}</p><form id="operation">${select(
    "action",
    "Operation",
    [
      ["process", "Start processing"],
      ["pack", "Mark packed"],
      ["ship", "Dispatch"],
      ["deliver", "Mark delivered"],
      ["shipment", "Update carrier state"],
      ["rto-inspect", "Inspect returned-to-origin stock"],
      ["collect", "Record COD collection"],
      ["remit", "Record carrier remittance"],
      ["refund", "Record reconciliation refund"],
      ["cancel", "Cancel before dispatch"],
    ],
  )}${field("tracking", "Tracking reference (dispatch)", "text", o.tracking, false)}${select("status", "Carrier state", ["Out for delivery", "Delivery failed", "RTO initiated", "RTO in transit", "Returned to origin"])}${field("reference", "Collection, remittance or refund reference", "text", "", false)}${field("amount", "Refund amount (paise)", "number", o.total - o.refund, false)}${field("reason", "Inspection note", "text", "", false)}<label class="check"><input type="checkbox" name="restock"> Restock inspected goods</label>${button("Apply operation")}</form><h3>Returns</h3>${o.returns.map((r) => `<div class="panel"><p>${esc(r.sku)} × ${r.quantity}: ${esc(r.status)}<br>${esc(r.reason)}</p><form id="return-${esc(r.id)}">${select("status", "Next status", ["Approved", "Rejected", "Received", "Closed"])}${field("reason", "Decision / inspection note")}${field("amount", "Refund amount in paise (0 for manual exchange)", "number", 0)}${field("reference", "Refund / exchange reference", "text", "", false)}<label class="check"><input type="checkbox" name="restock"> Restock after inspection</label>${button("Update return")}</form></div>`).join("") || "<p>No returns.</p>"}<div class="timeline">${o.timeline.map((t) => `<p>${esc(t.message)}<small>${date(t.at)}</small></p>`).join("")}</div></div>`;
  document.querySelector("#back-admin").onclick = () =>
    adminContent().catch((e) => toast(e.message));
  formHandler("operation", async (d) => {
    d.amount = Number(d.amount);
    d.restock = d.restock === "on";
    const updated = await api("/admin/orders/" + o.id, "POST", d);
    toast("Order updated");
    await adminOrder(updated);
  });
  o.returns.forEach((r) =>
    formHandler("return-" + r.id, async (d) => {
      const updated = await api("/admin/orders/" + o.id, "POST", {
        ...d,
        action: "return",
        return_id: r.id,
        amount: Number(d.amount),
        restock: d.restock === "on",
      });
      toast("Return updated");
      await adminOrder(updated);
    }),
  );
}
async function boot() {
  try {
    session = await api("/session");
    await refreshBag();
    await navigation();
    if (session.sandbox)
      document.querySelector("#mode").textContent =
        "LOCAL TEST STORE · Sample products and delivery rules · No real payments";
    document.querySelector("#account-link").textContent = session.user
      ? session.user.name.split(" ")[0]
      : "Account";
    const path = location.pathname;
    if (path === "/") await shop(true);
    else if (path === "/shop") await shop();
    else if (path.startsWith("/products/")) await product();
    else if (path === "/cart") await cart();
    else if (path === "/account") await account();
    else if (path === "/checkout") await checkout();
    else if (path === "/orders" || path.startsWith("/orders/")) await orders();
    else if (path === "/admin") await admin();
    else if (path === "/policies") policies();
    else if (path === "/reset-password") await reset();
  } catch (e) {
    main.innerHTML = `<div class="wrap"><h1>We couldn't load this page.</h1><p class="error">${esc(e.message)}</p><a href="/" class="button">Back to the store</a></div>`;
  }
}
async function navigation() {
  const { items } = await api("/categories");
  document.querySelector('nav[aria-label="Main navigation"]').innerHTML =
    '<a href="/shop">Shop all</a>' +
    items
      .filter((c) => !c.parent_id)
      .map(
        (c) =>
          `<a href="/shop?category=${encodeURIComponent(c.id)}">${esc(c.name)}</a>`,
      )
      .join("");
}
function profileForm(user) {
  const box = document.createElement("section");
  box.className = "panel";
  box.innerHTML = `<form id="profile"><h2>Your profile</h2>${field("name", "Display name", "text", user.name)}${button("Save profile")}</form>`;
  document.querySelector(".account-grid").append(box);
  formHandler("profile", async (d) => {
    session.user = await api("/me", "PATCH", d);
    toast("Profile updated");
    await account();
  });
}
boot();

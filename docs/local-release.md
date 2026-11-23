# Shared-store implementation and PRD status

21 November 2026. This is a runnable local MVP, not a signed-off production launch.

## What runs now

The new application is `app.commerce:app`. The original category-only service (`app.main:app`) and isolated rehearsal (`mock_store.main:app`) remain available separately.

| PRD area | Implemented in the shared store | Remaining work |
|---|---|---|
| Identity | Registration, scrypt password hashing, rotating HttpOnly sessions, CSRF and Origin validation, login throttling, logout, single-use recovery, profile API and saved addresses | Account verification, operational privacy/deletion process, external security review |
| Catalog | Categories with cycle checks and parent visibility; products, URL slugs, media URLs/alt text, size guides, draft/published/archived state, unique SKUs and size/colour combinations, collections | Object-storage uploads, richer attributes and merchandising controls |
| Storefront | Responsive home, search, category/size/colour/availability/price filters, sort, image gallery, variants, bag, login, address book, checkout, orders and policies | Final brand and content; broader accessibility/performance audit; popularity ranking |
| Checkout | Integer-paise server pricing, coupons, configurable PIN coverage, shipping/free-shipping/COD thresholds, additive tax setting, expiring server quotes, immutable order snapshots, idempotency | Business-approved tax treatment, prices and delivery rules; item-level COD restrictions |
| Inventory | Shared balances, atomic checkout reservations, guarded adjustments, cancellation/expiry release, consumption at dispatch, inspection-controlled restock | Per-SKU relational tables and movement reporting for larger deployments |
| Prepaid | Explicit sandbox success/failure/delay, retries, HMAC-authenticated callback, duplicate events, late-payment reconciliation | Selected hosted gateway, provider-specific signatures and transaction/settlement reconciliation; live refunds |
| COD | Eligibility, due/collected/remitted recorded independently, required collection/remittance references | Carrier collection and remittance integration |
| Operations | Server-enforced staff roles, catalog/stock/rule/promotion screens, process/pack/ship/deliver, tracking, failed delivery and RTO, audit before/after records | Carrier labels/webhooks, advanced search/reporting, permission-specific field redaction |
| Returns | Delivered-item quantity limits, configurable return window, approval/rejection/receipt/inspection, bounded partial manual refund, exchange resolution reference | Automated pickups, replacement orders and provider refunds |
| Notifications | Durable outbox; in-account timeline; SMTP worker with retries and stable Message-ID | Configure/verify SMTP. Delivery is at-least-once: a crash after SMTP acceptance but before commit can duplicate email |
| SEO | Server-rendered product name/description/price microdata, metadata, canonical URLs, robots and sitemap | Fully server-rendered interactive pages and production SEO validation |
| Launch | Local launcher, Docker/PostgreSQL configuration, tests and setup commands | Hosted staging, HTTPS, secret injection, monitoring/alerts, backup restore rehearsal and UAT sign-off |

## Architecture decisions

The runnable frontend uses HTML/CSS/JavaScript served by FastAPI. It does **not** implement the recommended Next.js/TypeScript/Tailwind/shadcn stack. This keeps local operation to one Python process and reuses the supplied image library. Product content has server-rendered fallback markup; interactive features require JavaScript.

Identity, sessions and reset tokens have dedicated SQLAlchemy tables. Commerce records use a shared JSON aggregate in `commerce_state`, separately from the original foundation schema. SQLite `BEGIN IMMEDIATE` or PostgreSQL `SELECT ... FOR UPDATE` serializes updates. Two customers cannot reserve the same last unit. All reads/writes currently take the aggregate lock: this is a small-store correctness-first design, not a high-throughput production data model. The original normalized catalog and Alembic migration remain intact. New tables initialize through SQLAlchemy; versioned commerce migrations and splitting the aggregate into the PRD's relational domain tables remain before scaling/production approval.

The actual API is documented at `/docs` and `/openapi.json` on the new service. `docs/openapi.json` remains the original foundation/design contract; it does not describe the new service's implemented route set.

Passwords and raw session/reset tokens are not stored in their identity tables. Pending reset email temporarily contains the delivery token in the outbox; the worker removes it after delivery or expiry. Staff APIs redact it. A local sandbox CLI helper can display the queued recovery token. Use `--no-access-log`: application logs contain request IDs, route templates, status and duration, excluding bodies, addresses, email query strings and tokens.

## Sample data

- Four products, 32 variants, ten simulated units per variant. These are not actual business stock.
- `500001`: prepaid/COD, ₹40 shipping, ₹20 COD fee, ₹1,499 free-shipping threshold, ₹5,000 COD ceiling.
- `520001`: prepaid only, ₹40 shipping, ₹1,499 free-shipping threshold.
- `WELCOME10`: 10% discount with a 100-use test limit. Tax is zero in sample rules.
- Seeding is repeatable and does not overwrite an existing catalog.
- No default administrator password; use `python -m app.manage owner`.

## Worker and recovery

Run `python -m app.manage worker` alongside the server. It checks expiry every 30 seconds; requests also expire pending holds. `--once` performs one pass.

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, optional `SMTP_USER`/`SMTP_PASSWORD`, and `PUBLIC_ORIGIN` for delivery. SMTP requires STARTTLS with certificate validation. Without SMTP, notices remain queued; confirmation remains available in the account.

For local recovery testing, request a reset through the UI, then run:

```powershell
.\.venv\Scripts\python.exe -m app.manage recovery-token --email your-test-account@example.test
```

Paste the token into the recovery form. It expires in 30 minutes, is single-use, and successful recovery revokes existing authenticated sessions.

## Payment boundary

`PAYMENT_MODE=sandbox` is the default. Pending-order buttons simulate success/failure without collecting card details or contacting a provider. A non-sandbox mode disables test payment endpoints and rejects prepaid checkout until a live adapter is implemented.

The optional callback is `POST /api/v1/payments/webhooks/sandbox`. Configure `PAYMENT_WEBHOOK_SECRET`. Send `order_id`, `event_id`, `amount` (integer paise), and `currency: "INR"` in JSON. `X-Signature` contains the lowercase HMAC-SHA256 hex digest of the original bytes. This is a fixture protocol, not a Razorpay/Stripe integration.

Staff refunds record an externally completed manual refund or exchange reference; they do not send money. Late captures after cancellation/expiry require reconciliation and cannot trigger shipment.

## Backups and launch

For local SQLite, stop the server and worker before copying `commerce.sqlite3` to protected storage. Restore into a separate installation and verify account/order/stock data before replacing an active database. Do not expose this local default to the internet.

For PostgreSQL, use `pg_dump` and verify restoration into a separate database. Compose uses a named volume; `docker compose down` preserves it. No production restore/rollback drill or hosted deployment has been completed.

Before public traffic: approve catalog/policies/support details and PINs; integrate real providers; normalize and migrate the production schema; configure TLS/secure cookies; validate on PostgreSQL; run security, accessibility, load and cross-browser checks; verify backups/alerts/staff procedures; obtain launch sign-off. Wishlist, reviews, loyalty and recommendations remain deferred P1/P2 work.

## Verification completed

- SQLite suite: 29 passed; one PostgreSQL-only test skipped.
- PostgreSQL 16 suite: 30 passed, including atomic last-unit checkout and the original Alembic migration/readiness check. Each commerce test used an isolated schema.
- JavaScript rehearsal regression suite: 13 passed.
- Chromium browser suite: 3 passed (390px mobile checkout, 1440px catalog/gallery, owner draft/stock/audit). Screenshots were visually reviewed.
- Windows launcher: started on an alternate port and returned readiness HTTP 200.
- Docker: built the store image; non-root container returned HTTP 200 for readiness, homepage and JavaScript. Compose configuration validated. No hosted CI run or production deployment was performed.

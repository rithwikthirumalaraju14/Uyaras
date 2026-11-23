# T-shirt Studio · mock release
20 November 2026

## Walk through the store

1. Open the private store or standalone HTML. Choose a style, colour and size. Add it to the demo bag and change the quantity.
2. Continue to checkout and choose the seeded demo shopper, or create a fictional alias and add a sample address. Choose a test area and payment method. The quote shows item prices, discount, test shipping, test tax and total.
3. Try AP-DEMO for prepaid or COD, TG-DEMO for prepaid only, and Outside demo coverage for a blocked order. Use TEE10 for an illustrative 10% discount. Actual shipping fees, COD policy, customer prices, tax and PIN coverage are undecided.
4. Choose failed, delayed or successful prepaid payment. A delayed order can receive a mock event or expire. Rehearse reconciliation if a successful receipt arrives after release.
5. In Staff, enter the Owner or Operations role. Open the order, process it, mark it packed, dispatch it and mark it delivered. For COD, record collection and then remittance. A failed delivery can be returned to origin for inspection.
6. Switch back to Orders and open the delivered order. Select the item, quantity and reason to request a return or exchange. In Staff, approve or reject it, record receipt, then record inspection and resolution. A closed refund request updates the amount refunded. Exchanges use a manual resolution record.
7. In Staff, try the Catalog, Inventory, Shipping, Promotions, Customers, Roles and Audit tabs. Adjust stock with a reason. Change a sample price and compare it with the snapshot on an existing order. Try Analyst to see the read-only workflow.

The private site and standalone file keep their own local browser state. The FastAPI version keeps an isolated fictional store for each browser session in SQLite. Use the same browser and mode to resume a rehearsal. Browser aliases and staff role selectors deliberately let the tester switch perspectives within their own sandbox.

## PRD coverage and release boundary

| PRD sections | Evidence in the mock | Still required for a production release |
|---|---|---|
| 1–4 · Business and scope | Single-brand men’s and women’s T-shirts. Four styles, eight product images, 32 initial variants. Three simulated units per variant allow checkout rehearsal. Actual stock remains zero. | Approved brand, merchandising, real inventory and commercial offer. Wishlist, reviews and other post-MVP features remain deferred. |
| 5, 10–11 · Architecture, entities and APIs | Reusable rules shared by the browser and transaction-backed FastAPI simulator. Original PostgreSQL migration, six ER diagrams and target OpenAPI contract included. | Implement the production domain APIs and Next.js storefront. Existing production foundation implements catalog categories and probes. The SQLite demo uses a separate command interface. |
| 6, 12 · Customer and design | Search, filtering, sorting, product gallery via colour selection, size guides, bag, mock accounts, saved addresses, quotes, order history, tracking, policies and support placeholders. | Production authentication, verified password reset, accessible final content, SSR and SEO. Real support details and business-approved policies. |
| 7 · Staff | Roles, product drafts, images selected from a fixture library, publish/archive, size/colour SKUs, collections, simulated stock balances, audited adjustments, orders, payment ledger, shipping, rates, promotions, returns and profiles. | Harden staff provisioning, extend taxonomy and media uploads/storage, inventory reporting, granular permissions and detailed compliance logging. |
| 8–9 · Workflows and states | Separate order, payment, shipment, return, COD collection and remittance state. Simulated retry, delayed capture, expiry, cancellation, RTO and item-level refund. Order history includes the event timeline. | Provider-authoritative tracking, background reservation expiry and retries, outbound email/SMS delivery, finance settlement and operational exception handling. |
| 13–15 · Quality and safeguards | Quote recalculation, price snapshots, nonnegative available stock, retry keys, duplicate payment-event handling, role and order ownership checks in the rule engine. FastAPI demo adds a database transaction and accepts signed mock callback fixtures. | Production-grade security review, PostgreSQL concurrency/load tests, accessibility audit, Core Web Vitals, cross-browser and device testing, backups/restore and monitoring. |
| 16–20 · Delivery and readiness | Baseline PRD, wireframes, estimated tickets, decision log, machine-readable contract, implementation and regression checks. | Provider selection, real content, checkout policies, staging UAT, operations training and launch sign-off. |

## Verification

- Python suite: 14 passed; the existing PostgreSQL integration case was skipped because a migrated PostgreSQL test database was unavailable in the execution environment.
- Business-rule suite: 13 passed under Node. Coverage includes stale quotes, repeated order keys, duplicate and late payment receipts, COD restrictions, last-unit reservation, shipment, return to origin, partial returns, refunds and permission checks.
- The FastAPI tests exercise signed mock callbacks, rejection of invalid signatures, repeated events, isolation between sessions and rollback on a rejected stock change. Two concurrent order requests for the last seeded unit yielded one order and one conflict in the SQLite simulator.
- Browser rehearsal: selected the women's boxy pocket tee, added it to a guest bag, used the demo account at checkout, confirmed a simulated prepaid order, then advanced it through processing, packing, dispatch and delivery. The tracking reference and event timeline appeared on the order.
- The private deployment uses the standalone browser mode. The owner signs in with ChatGPT to open the site. Private-site access and the simulated in-store roles serve different purposes.

## Optional signed fixture adapter

The database-backed demo exposes POST /mock/provider/payment-event when STUDIO_MOCK_WEBHOOK_SECRET is configured for the local test process. The payload contains order_id, event_id, amount (whole test rupees) and currency (INR). X-Mock-Signature contains the HMAC-SHA256 hex digest of the original JSON bytes. The integration test supplies a temporary fixture secret and replays the same captured event twice. The production design uses integer paise, provider-specific signatures, unique transaction/event IDs and dedicated payment records.

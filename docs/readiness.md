# PRD v1.0 engineering review
Historical foundation review. For the shared-store implementation added on 21 November 2026, see [local release status](local-release.md) and the [run guide](../README.md). Items below describe the earlier milestone, not the current implemented feature set.
20 November 2026 · Baseline for the first development milestone

**Current catalog update:** Begin with mock men’s and women’s T-shirts. Andhra Pradesh and Telangana are under consideration for delivery. No PINs, charges, COD rules or physical inventory have been confirmed. All demo variants have zero stock.

**Decision:** Start Phase 1 and the catalog schema. The single-brand regional model, customer journey, inventory unit, technology stack and delivery sequence are sufficiently specified. Store launch and vendor commitments require business input. The decisions below are reversible proposals for review.

| PRD reference | Working interpretation | Decision due |
|---|---|---|
| §§4, 6.2, 16 · Wishlist | Defer the feature and its navigation entry to P1. Keep cart persistent. | Before storefront navigation is frozen |
| §§4, 7, 16 · Promotions and returns | Model discounts from the outset. Prioritize audited manual returns/refunds and simple offers. Schedule coupon automation, exchanges automation and marketing analytics in P1. | Before checkout acceptance |
| §§6.10, 16 · Notifications | Order confirmation in the account is P0. Provide a minimal transactional confirmation channel before launch. Additional channels and campaigns follow. | Provider and support contact before fulfilment |
| §§6.6, 8 · Guest access | Browse and cart without login. At checkout, sign in and attach or merge the anonymous cart once. Revalidate quantities, price and availability. Preserve selections if sign-in fails. | Before account and cart implementation |
| §§8, 14 · Reservation timing | Viewing a cart or requesting a quote never holds stock. Place the hold during the atomic order-creation step, before opening the prepaid gateway. Keep expiry configurable. | Before checkout coding |
| §§9, 10 · Refunds and COD | Payment capture, order status, physical delivery and COD remittance have independent records. Manual partial returns live at the item level. | Before operations screens |
| §§5, 18 · Runtime | Start with FastAPI, PostgreSQL and Alembic in a modular monolith. Plan Next.js App Router and TypeScript for storefront. Docker Compose supplies a local environment. Hosting and staging account remain open. | Staging provider before deployment |
| §§2, 12, 18 · Launch data | One initial inventory location, INR integer paise, India PIN format and configurable categories. Keep actual launch records empty until supplied. Design labels and values are examples. | Business-supplied content before pilot |

## What the business needs to supply

| Milestone | Input and accountable role | What can proceed now |
|---|---|---|
| Catalog onboarding | Founder / merchandising: first products, photos and usage rights, category labels, sizes, colour names, size-guide units and measurements. | Draft schemas, upload metadata, configurable category management |
| Storefront design sign-off | Founder / design: brand name, wordmark, fonts, accent and visual references. | Low-fidelity responsive layouts and component behavior |
| Checkout sandbox | Finance / operations: price and tax treatment, discount ordering and rounding, shipping and COD fees/limits, free-shipping and reservation expiry rules, launch PINs and exceptions. | Design money ledger, quote expiry, PIN and eligibility checks |
| Fulfilment pilot | Operations: origin and warehouse details, cut-off, expected delivery windows, cancellation stages, return eligibility/window, exchange process and refund approvals. | Implement transition guards and audit trail with test fixtures |
| Staging and launch | Founder / engineering: traffic and budget estimate, hosting and monitoring choice, approved gateway, carrier, notifications and sandbox accounts. Supply legal text and staffed contacts. | Local build and CI configuration, provider-neutral interfaces |

## Transaction and contract decisions

- **Session and access.** Separate a short-lived anonymous cart identity from a customer session. Rotate session after login, validate origin and session CSRF token on cookie-backed writes, scope customer records to the authenticated user, and check staff permissions for every admin endpoint. Restrict staff role changes to authorized owners. Apply rate limits to login, registration and reset flows. Store hashed tokens and omit raw credentials, addresses, PINs, request bodies and query strings from application access logs.
- **Checkout.** Lock the cart version and price the quote using server-held address and rates. Within one database transaction, claim the idempotency key, verify the quote, create an order and immutable snapshots, acquire variant balances in stable location/SKU order, increase reserved quantities conditionally, and consume the cart. Roll back every write on any insufficient balance. Enforce one order per consumed cart version with a database uniqueness rule. On retry, return the existing resource. A changed payload on the same key returns HTTP 409.
- **Payment and stock.** Gateway requests run outside the database transaction and carry a provider idempotency reference. A durable job retries uncertain attempts. The provider adapter validates event signature, external reference, expected amount and currency. Persist the inbox event and effect atomically. At dispatch, decrease both on-hand and reserved. Release each unfulfilled hold once on expiry or approved cancellation. A late success after release triggers reconciliation and an eligible refund or reallocation under a new atomic stock check. Never silently confirm unavailable stock.
- **COD.** Check PIN, cart value and eligible items at final submission. Confirm the order with COD due. Record amount collected on delivery, then post the separate carrier remittance record during reconciliation. Refunds for collected COD orders need an approved manual refund method and settlement reference.
- **Shipping.** Reject unknown PINs by default. Display estimates only where configured. Deduplicate carrier events by provider and external event ID and persist the previous state, new state, source and time. Failed delivery can lead to another delivery attempt or RTO. Only restock after receipt and inspection.
- **Returns and refunds.** Enforce per-item cumulative return quantity against delivered quantity. Approval creates a return shipment or manual pickup. After inspection, record disposition, refund only against a paid transaction or collected COD balance, and cap cumulative refunds at captured net funds. Keep unaffected order items in place.
- **Tax and totals.** Store integer paise and the quoted breakdown on each order. Inclusive vs exclusive price presentation, line-level rounding and coupon/tax order require finance approval. A changed quote requires customer review. Avoid double-counting included tax.
- **Public catalog.** Only reachable published categories and published products with visible parent scope appear publicly. Empty categories and absent stock are valid. Validate hierarchy edits against cycles and archive referenced records.
- **API lifecycle.** docs/openapi.json is the design contract. The running service exposes its implemented subset at /openapi.json. Payment and carrier signatures, wire payloads, settlement imports and notification delivery adapters require vendor-specific fixtures after selection.

## Workflow boundaries for implementation

| Domain | Allowed main transitions | Exceptions and review |
|---|---|---|
| Order | Draft → pending payment (prepaid) or confirmed (eligible COD) → processing → packed → shipped → delivered → closed | Eligible pre-dispatch orders may request cancellation. Rejection restores recorded prior state. An accepted full return moves delivered → return requested → returned → closed. Partial returns remain on individual items. |
| Payment | Pending → authorized → paid, or pending → paid on verified capture. Paid → partially refunded → refunded. COD due → collected. | Failed attempts remain terminal. A retry creates a new attempt. Duplicate capture events apply once. |
| Reservation | Active → consumed at dispatch, or active → released on approved cancellation / expiry | Database balance checks apply to every transition. A confirmed COD hold stays active until cancellation or shipment. |
| Shipping | Not created → label created → picked up → in transit → out for delivery → delivered | Delivery failed → out for delivery or RTO initiated → RTO in transit → returned to origin. |
| Return | Requested → approved → in transit → received → inspected → closed | Requested → rejected. Record a rejection reason or refund reference. |

## Definition of done for the foundation milestone

A clean PostgreSQL environment upgrades through Alembic; health and readiness probes reflect process and schema state; sessions, reset and permission-negative tests pass; logs exclude sensitive material; the CI job passes on a hosted runner. Deploy to a test environment, test a restore and document rollback. Current work completes the first source slice. Identity, hosted validation, deployment and restore remain open.

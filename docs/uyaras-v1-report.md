# Uyaras V1 completion report

Uyaras now has a working commerce development preview on the approved stack. The earlier plain HTML frontend and single JSON commerce record have been replaced in the default application by Next.js and normalized PostgreSQL. Real payments, dispatch and production ordering remain disabled, as requested.

## Built for this version

| Area | Delivered behavior |
| --- | --- |
| Brand | Blue and off-white visual identity, wave wordmark, reusable SVG logo/icon, serif editorial headings and readable sans-serif UI. No song artwork or lyrics copied. |
| Frontend | Next.js App Router, React, TypeScript, Tailwind and generated shadcn/ui button primitives; responsive storefront and staff studio. |
| Backend | FastAPI, Pydantic request/public response contracts, SQLAlchemy 2, PostgreSQL and Alembic migrations; separate security, catalog, checkout, media and provider modules. |
| Discovery | Home, configurable category navigation, collections, new arrivals, popularity sorting, offers, search and price/size/colour/availability filters. Product and policy pages render on the server. |
| Products | Galleries, size/colour selection, SKU availability, size guides, care information, sample price labels, PIN checks, metadata and structured product information. |
| Accounts and cart | Guest bag; merge at registration/login; profile and saved addresses; session rotation, logout and password recovery; sign-in before checkout. |
| Checkout | Server quotes and totals, tax-inclusive sample prices, shipping/free-shipping/COD rules, one non-stacking percentage coupon, scoped eligibility, atomic stock holds and idempotent order creation. |
| Payments | Configurable mock boundary, success/failure simulation, signed mock webhooks, event deduplication, failed/expired hold release, retry, late-capture reconciliation and payment-attempt visibility. |
| Operations | Catalog/category/collection/SKU editing; inventory adjustments and thresholds; movements/reservations; staff permissions; order actions; manual shipment references/milestones; RTO; separate COD collection/remittance. |
| After-sales | Customer return/exchange requests, staff approval/rejection/pickup/receipt/inspection, optional inspected restock, manual resolution references and refund records capped by collected order amount. |
| Media | Sample project images plus R2 presigned upload and verified image confirmation; editable descriptions/order and product-image detachment. No account or credentials fabricated. |
| Configuration | Editable homepage text, prices, catalog, PIN rules, charges, coupon rules, policies, support/warehouse details and provisional tax settings. |
| Reliability | PostgreSQL integration tests, reservation worker, notification outbox with SMTP adapter, safe request metadata logging, backup/restore scripts, Docker definitions and GitHub Actions workflow. |

## Provisional business settings

The [market research](market-research.md) compares first-party Indian clothing-store prices and policies. The implementation uses these **test assumptions**:

- Sample T-shirts at ₹499, ₹599 and ₹699.
- ₹49 delivery; free when discounted merchandise reaches ₹999.
- ₹39 COD fee; maximum payable COD total ₹3,000.
- Explicit test PINs 500001 and 520001. These are not verified courier coverage.
- Editable sample delivery estimate of 3–7 working days.
- Fourteen-day return request window; manual approval, inspection and refund/exchange handling.
- Five-percent inclusive demo tax. Actual GST registration, product classification and transaction treatment remain unconfirmed.
- WELCOME10: ten percent off, minimum merchandise subtotal ₹999, limited use count. One coupon per order; no stacking.

Warehouse and support details remain empty. No fake phone number, business address, courier account or live payment credentials have been added. The budget assumption remains ₹1,500–₹3,000/month; hosting is not selected or purchased.

## Verification

### V1 completion follow-up — 22 November 2026

Added dynamic catalog facets and pagination, fabric and regular-price fields, product-level COD restrictions, guest cart estimates with allocated discounts, saved-address editing, paginated order history, customer cancellation requests with staff approval/rejection, all six suggested staff roles, administrative server-side search, consistent API error envelopes, sensitive mutation rate limits, richer audit/timeline records and channel-neutral email outbox metadata. Wishlist remains hidden.

Checkout now waits for saved-address loading before accepting a new address, preventing a delayed response from overwriting newly saved data. Long cancellation reasons remain on the order while timeline messages respect database length limits.

The [acceptance matrix](uyaras-v1-acceptance.md) maps each PRD section 15 criterion to named tests and distinguishes mock evidence from launch dependencies. The [provider comparison](provider-comparison.md) proposes options for approval; no real provider integration has been selected or added. The [OpenAPI snapshot](uyaras-openapi.json) reflects the expanded API.

Backend evidence: the full run passed 19 tests with one setup error while PostgreSQL was starting; that test passed individually after readiness. The expanded completion file passed all six tests (including four overlapping that full run), giving 22 distinct passing tests across runs. A Starlette/httpx test-client deprecation warning remains; it does not indicate a failed application test. Frontend lint and production build passed.

Both Docker images built successfully. The isolated container rehearsal passed migrations, zero-stock catalog seed, frontend rendering, API proxy, session/CSRF cart mutation and worker execution. It caught a missing catalog seed file in the API image; the Dockerfile now includes it. Test containers/network were cleaned up. The store database was upgraded to `uyaras_0004`. This verifies local container deployment, not public staging.

Browser evidence: the expanded run passed 11 of 12 checks. WebKit's skip-link keyboard check exposed a missing explicit tab stop; the skip link now declares `tabIndex=0` and main content accepts programmatic focus with `tabIndex=-1`. The failed WebKit check passed on targeted rerun. All 12 checks therefore have passing results across runs. Chromium keyboard review also confirmed Tab to skip link, Enter to main, then Tab to catalog search. Selected automated axe checks passed; complete manual WCAG and real-device performance acceptance remain pending.

GitHub Actions now includes both image builds and an isolated container smoke test. Remote CI has not run: this workspace has no Git repository/remote, and the owner's repository destination is still needed.

### Earlier preview baseline (historical)

Sixteen PostgreSQL integration tests passed, covering concurrent last-unit checkout, idempotency, ownership/CSRF/roles, recovery links and session invalidation, stock expiry/retry, late capture, COD fulfillment, returns/restock, refund limits, quote invalidation, promotion eligibility, immutable snapshots, repeated login cart preservation, fresh migrations, the production lock, the R2 adapter with a test double, and database commit visibility before an HTTP success response.

Nine browser checks passed: three journeys each in Chromium, Firefox and WebKit. They cover mobile discovery with automated WCAG-tagged checks on home/product pages; guest bag through registration, checkout, prepaid failure/retry/success and cancellation; and staff category/settings/audit operations. Session initialization is shared between concurrent frontend requests, and checkout tests wait for navigation before filling the delivery form.

Frontend lint and the optimized Next.js production build passed. Both the Windows setup-only launcher and full startup command passed; the full command starts PostgreSQL, the API, reservation/notification worker and Next.js. A PostgreSQL custom-format backup restored successfully into a separate database at migration `uyaras_0003`, containing four sample products and zero orders. The production data volume was not overwritten. Dependency audit reported no frontend production vulnerabilities at the time checked.

Docker definitions are included. The frontend image built successfully; the optional API image build was stopped during very slow dependency downloads, so the complete container deployment is not verified. The tested Windows launcher uses local Python/Node processes and Docker PostgreSQL. The GitHub Actions workflow is provided but has not run on a remote repository.

Automated accessibility checks cover selected screens and do not certify WCAG conformance. Real device/network performance, external provider delivery and public deployment are separate launch acceptance work.

## Remaining before a real launch

1. Enter actual garments, owned photographs, measurements, prices and verified inventory. Current catalog data and all simulated stock/orders are disposable.
2. Confirm GST handling, shipping/COD economics, AP/Telangana PIN serviceability, warehouse/return address, dispatch process, support contact and final legal/policy content.
3. Select payment and shipping providers. Implement their actual create/verify/refund/label/webhook contracts and complete sandbox acceptance. Razorpay and Shiprocket have not been selected.
4. Supply and test R2 and SMTP credentials. R2 code is implemented, but no live bucket round trip has been performed.
5. Choose hosts and domain, configure HTTPS, monitoring/alerts, encrypted off-site backups and retention, then complete staff and customer acceptance on the deployed environment.
6. Review and deliberately remove the server-side production ordering gate only after those conditions are satisfied. Changing an admin checkbox alone cannot enable sales.

The mock V1 uses one primary warehouse, fixed server-enforced role sets, one primary category per product with multiple collections, and manual refund/exchange/shipping operations. It does not implement arbitrary multi-role permissions, automated exchanges, carrier labels, live settlement polling or an advanced analytics platform. Wishlist, reviews, loyalty, AI, native applications and multi-warehouse allocation remain deferred under the agreed scope. Percentage coupons are implemented; fixed-amount promotions are not part of this preview.

## Run and review

Follow the [README](../README.md) for the short startup flow, the [operations guide](uyaras-operations.md) for owner access and tests, and the [architecture guide](uyaras-architecture.md) for database boundaries and state transitions. The original [PRD](clothing_ecommerce_prd_v1.pdf) has not been rewritten.

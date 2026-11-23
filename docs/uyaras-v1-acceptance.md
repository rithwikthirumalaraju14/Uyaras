# V1 acceptance evidence

The PRD remains the specification. Passing mock tests does not mean launch approval. Run backend checks with `pytest backend/tests -q` after loading the development environment; run the browser suite with `python scripts/browser-test.py`. Both use disposable PostgreSQL schemas.

## PRD section 15 traceability

| Criterion | Named automated evidence | Remaining real-world acceptance |
| --- | --- | --- |
| Catalog | `test_prd15_catalog_configurable_filters_and_pagination`; browser `mobile storefront, filters and accessible product controls` and `catalog pagination preserves filters and keyboard navigation` | Real catalog, photography, sizes and staff approval |
| Variant stock | `test_category_cycles_and_inventory_constraints`; `test_prd15_cod_pin_value_product_and_cart_estimate` | Enter and reconcile actual inventory |
| Checkout totals | `test_idempotency_cart_and_tax_snapshot`; `test_quote_invalidated_by_price_or_cart_change`; `test_promotion_eligibility_and_item_snapshot` | Approve actual taxes, prices and delivery charges |
| Serviceability | `test_prd15_cod_pin_value_product_and_cart_estimate`; browser unsupported-PIN check | Verify pickup and delivery lanes with selected carrier |
| Prepaid payment | `test_signed_webhook_idempotency`; `test_expiry_retry_and_late_capture`; browser `guest bag merges after registration; prepaid failure, retry and capture` | Selected gateway sandbox signatures, refunds, reconciliation and public webhook |
| COD | `test_prd15_cod_pin_value_product_and_cart_estimate`; `test_cod_fulfillment_returns_and_refund_caps` | Carrier confirmation, collection and remittance evidence |
| Inventory concurrency | `test_last_unit_concurrent_checkout`; `test_expiry_retry_and_late_capture` | Repeat against staging PostgreSQL configuration |
| Order snapshots | `test_snapshot_survives_catalog_edits_and_relogin_preserves_cart`; `test_promotion_eligibility_and_item_snapshot` | Staff acceptance of actual invoice/tax treatment |
| Authorization | `test_security_ownership_csrf_and_roles`; `test_prd_api_envelopes_address_edit_search_and_roles`; `test_production_is_locked_and_settings_cannot_bypass` | Named staff accounts and access review |
| Operations | `test_cod_fulfillment_returns_and_refund_caps`; `test_prd_cancellation_request_approval_and_audit`; browser `staff studio catalog, configuration and audit` | Staff rehearsal using approved shipping/returns policies |

## Additional requirements

- Six roles: Owner, Administrator, Catalog Manager, Operations Manager, Support Agent and Read-only Analyst. Staff access management is Owner-only. Server-side permissions apply independently of visible admin tabs.
- Cancellation Requested: customer reason, staff approval/rejection, stock release after approval and paid-order refund-required state. Long reasons are retained on the order; timeline summaries are bounded.
- Sensitive mutation throttling: `test_sensitive_mutation_rate_limit_and_recovery`. Authentication endpoints have their own counters. This is application protection; edge bot controls remain a deployment task.
- Notifications: `test_email_retry_exhaustion_and_channel_isolation`. Email worker retries with backoff, stops after eight attempts and leaves other channels untouched. Actual SMTP delivery remains unverified.
- Error envelopes, ownership, address editing and server search: `test_prd_api_envelopes_address_edit_search_and_roles`.
- Collection routes use page/page_size and return items/total/page/page_size/pages. Finite metadata such as facets and bounded saved addresses retain their specific response shapes.
- Fresh database migrations: `test_fresh_alembic_migration`. R2 validation is exercised with a test double by `test_r2_adapter_validates_and_manages_image_metadata`; live bucket acceptance is pending.
- Container deployment rehearsal: `scripts/container-smoke.py` builds on separately built API/frontend images and exercises a fresh disposable database, migration, zero-stock seed, storefront, API proxy, CSRF cart mutation and worker.
- GitHub Actions is configured for backend, browser, lint/build and both container images plus smoke testing. A remote run requires the owner's repository destination.

## Performance and accessibility release gates

Proposed launch budgets: mobile p75 LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1; initial storefront transferred assets <= 1.5 MB; representative catalog API p95 <= 500 ms under a documented staging load. These are targets, not achieved measurements. Measure production builds, record device/network/load conditions, and collect field data after launch.

`NEXT_PUBLIC_MEASURE_VITALS=true` enables fixed-name Web Vitals reports with coarse route buckets. Reports exclude URL query strings, order IDs and customer fields. Default is off. Set at frontend build time. The API logs observations; it does not yet aggregate percentiles or provide alerting dashboards.

`CATALOG_METADATA_TTL` defaults to zero. A positive value caches category/collection metadata only; stock, price, cart and customer responses stay fresh. Verify staff edits are visible within the selected cache interval.

Browser checks include keyboard access to the skip link, mobile overflow and axe scans on selected home, product and checkout states. The pagination/skip-link check passed in Chromium, Firefox and WebKit after adding an explicit skip-link tab stop and a focusable main target. An interactive Chromium check confirmed skip-link activation and subsequent focus on catalog search. These checks do not certify WCAG 2.2 AA. Manual release review must include all interactive flows with keyboard alone, visible/unobscured focus, error recovery, zoom/reflow, screen-reader labels/live announcements and touch target sizes. Public staging/device checks are pending.

## Launch dependencies

Provider approval and credentials; real stock/catalog; GST and policy review; verified PIN lanes and warehouse; support contact; SMTP/R2 round trips; hosts/domain/HTTPS; monitoring and alert routing; backup restore rehearsal on the deployed environment; privacy retention/deletion policy; staff acceptance. Production ordering stays locked until these are completed.

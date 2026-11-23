# API walkthrough

The complete target contract is in `openapi.json`. The service exposes its own executable OpenAPI schema at `/openapi.json`. Three operations currently run. The checkout examples below describe planned behavior and use illustrative identifiers.

## Running slice

| Request | Success | Failure to expect |
|---|---|---|
| GET /health/live | 200, status alive | A stopped process cannot answer. |
| GET /health/ready | 200, status ready, when PostgreSQL reports the expected migration | 503 if the database is unavailable or the revision is missing. |
| GET /api/v1/categories?page=1&page_size=24 | 200, published categories in stable slug/ID order | 422 for invalid pagination. 503 on database outage. |

A clean database returns `{"items":[],"page":1,"page_size":24}`. Every HTTP response carries an X-Request-ID header. An error body contains an error object with a stable code, a human-readable message and the same request ID.

## Proposed checkout exchange

1. The guest reads the cart. The server binds that cart to a session cookie and returns a CSRF token. Mutating calls include the token. When the customer signs in, rotate the session, merge the anonymous cart once and disclose stock or price changes.
2. POST /api/v1/checkout/quote reads the owned cart and address. Example request: `{"cart_version":4,"address_id":"addr-example","payment_method":"prepaid"}`. The response includes quote ID, expiry, delivery options and an itemized total. There is no stock hold at this step.
3. POST /api/v1/checkout/orders accepts `{"quote_id":"quote-example"}`, an Idempotency-Key and the CSRF token. On successful validation it returns HTTP 201 with a purchase-time snapshot. If stock sold out or the quote changed, return 409 and let the customer review the revised cart. A repeated key and matching payload returns the original committed result.
4. For prepaid, POST /api/v1/payments/create starts a hosted payment attempt for that order. A provider callback updates the attempt only after signature, amount, currency and reference checks. The customer reads the verified result. For COD, a successful order remains unpaid with COD due. Staff record collection and remittance separately.
5. Customers read GET /api/v1/orders/{id}/tracking. Customer order and return lookups are scoped to ownership. Staff use separate role-checked endpoints. Unknown and inaccessible customer resource IDs produce the same 404 response.

## Acceptance examples for later tickets

| Scenario | Required observation |
|---|---|
| Unsupported PIN, otherwise valid address | Serviceability gives a reason. Final submission cannot create an order, payment attempt or reservation. |
| Two customers request the last unit | One atomic reservation succeeds. The other request sees a stock conflict. Available stock stays nonnegative. |
| Duplicate captured-payment delivery | The same provider/event pair has one persisted effect; the order is confirmed once. |
| Paid event arrives after hold expiry | Persist the event, reconcile against availability and record a recovery outcome. No silent confirmation. |
| Product title or price edited after purchase | Prior order pages and refunds continue to use the immutable order-line snapshot. |
| One item from a multi-item order is returned | Returned quantity and refund apply only to that item and remain bounded by fulfilled quantity and collected amount. |

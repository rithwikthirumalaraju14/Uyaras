# Uyaras V1 provider comparison

Research date: **22 November 2026**. Scope: Indian prepaid payments and parcel shipping for an initial AP/Telangana T-shirt store, up to 500 orders/month. This is a proposal, **not an approved provider selection or a completed integration**. No accounts, subscriptions, shipments or payments were created. Public documentation was reviewed; no provider sandbox was exercised.

## Proposed shortlist

**Payment: Razorpay as the baseline candidate, Cashfree as the commercial alternative. Shipping: compare Shiprocket with direct Delhivery before choosing.** This recommendation is an engineering judgement based on the documented interfaces below, not a measured claim about uptime, local delivery quality or support. Both payment candidates expose the necessary refund and webhook primitives. Shiprocket offers courier choice; Delhivery offers a documented staging environment and a potentially shorter COD remittance cycle. Actual pickup coverage and the accepted rate card can change the shipping decision.

Keep the mock adapters while the owner reviews this comparison. Obtain explicit approval of the payment and shipping providers before implementing either integration. Approving this research does not approve opening accounts or buying a plan.

## Payment gateways

Payment gateways settle prepaid customer payments. They do **not** determine the courier's COD collection/remittance timetable, delivery PIN coverage or shipping-label format. Keep prepaid settlement and carrier COD reconciliation as separate ledgers.

| Criterion | Razorpay | Cashfree |
| --- | --- | --- |
| Published baseline fees | Pricing page advertises 2% plus GST, with no setup or annual maintenance charge; optional instant settlements cost extra. Use the actual method-specific merchant rate card when budgeting. [Pricing](https://razorpay.com/pricing/) | Standard rate shown in current offer terms is 1.95% plus applicable taxes after the offer ends. The offer has material conditions described below. [Pricing and offer terms](https://www.cashfree.com/payment-gateway-charges/) |
| Prepaid settlement | Pricing says typically T+1 or instant, while provider-owned settlement documentation says T+2 working days, subject to account/risk approval. Treat the merchant's confirmed schedule as authoritative; do not promise T+1. [Pricing](https://razorpay.com/pricing/), [settlement documentation](https://github.com/razorpay/markdown-docs/blob/master/payments/settlements.md) | Current eligible new-merchant offer specifies T+1 by 8pm IST during its campaign. Confirm the account's post-offer schedule and additional instant-settlement fees. [Offer terms](https://www.cashfree.com/payment-gateway-charges/) |
| Test environment and webhook design | Test-mode events use the same payload structure as live events. Raw-body HMAC-SHA256 verification and event-ID deduplication are documented. Public webhook URLs are necessary. Several tunnel domains, including `ngrok.io`, are blacklisted; the docs currently suggest `zrok`. Recheck URL acceptance before arranging a tunnel. [Webhook testing/validation](https://razorpay.com/docs/webhooks/validate-test) | Sandbox webhooks, raw-payload signatures, duplicate delivery and configurable retry policies are documented. The docs describe local tunnelling for tests. Pin an API/webhook version and verify the exact header contract with sandbox payloads rather than guessing header names. [Webhook overview](https://www.cashfree.com/docs/payments/online/webhooks/overview) |
| Refund API | Full/partial normal or instant refunds on captured payments; fetch refund status; test keys supported. [Refund API](https://razorpay.com/docs/api/refunds) | Refund creation includes merchant refund ID, amount and speed; the current API documents a six-month window from the successful transaction. A successful request is not evidence that the customer has received funds. [Refund API](https://www.cashfree.com/docs/api-reference/payments/latest/refunds/create-refund) |
| COD and labels | Carrier collection/remittance and shipping labels are outside this payment gateway comparison. | Same. A separate payout product, if later used for COD refunds, needs its own approval and reconciliation. |

**Cashfree promotion caveat:** the page currently advertises an offer through 31 March 2027, up to ₹20 lakh eligible domestic GMV. Terms restrict eligibility and payment methods, apply fair-use exclusions and reserve withdrawal rights. They explicitly retain GST calculated on the standard 1.95% rate even when the platform fee is waived. Thus “0%” must not be presented as zero total cost. Get written confirmation of eligibility, taxes and the post-offer rate before selecting on price. [Current terms](https://www.cashfree.com/payment-gateway-charges/)

For scale only: at an **assumed** ₹699 average prepaid order, 500 prepaid orders produce ₹349,500 monthly processed value. A 2% fee is ₹6,990 before tax; 1.95% is ₹6,815.25 before tax. These are arithmetic scenarios, not quotes; actual prepaid share, fees and refunds change the result. Transaction fees and postage are **business operating costs separate from the ₹1,500–₹3,000 hosting target**.

## Shipping and COD

| Criterion | Shiprocket aggregator | Direct Delhivery |
| --- | --- | --- |
| Fees | Current pricing lists Lite free, Business ₹199/month, Advanced ₹499/month and Pro ₹799/month, with illustrative average shipment costs. Those averages are not an AP lane quote. Its older comparison page shows different plans and limits API access to Advanced/Pro: obtain written confirmation of current API entitlement and all charges before committing. [Current pricing](https://www.shiprocket.in/pricing/), [conflicting comparison](https://www.shiprocket.in/price-compare/) | Exact pricing is in the account rate card. Charges depend on zone, mode, chargeable weight and forward/RTO/reverse movement; COD cash handling and other surcharges can apply. No dependable universal small-merchant price was established from public docs. [Rate card explanation](https://help.delhivery.com/docs/rate-card) |
| COD fee | Courier-specific fixed charge or percentage, whichever is higher. Calculate using pickup/delivery PIN, packed weight/dimensions and order value. Uyaras's sample ₹39 customer COD fee is not a carrier quote. [COD charge calculation](https://support.shiprocket.in/support/solutions/articles/152000000168-how-to-check-the-applied-cod-charges-) | Additional cash-handling charge is documented; obtain the account's amount/percentage and minimum. [Rate card](https://help.delhivery.com/docs/rate-card) |
| COD remittance | Support states D+8 working-day processing with Monday/Wednesday/Friday credits and up to ten working days for bank receipt. Early COD can be faster but is an optional commercial arrangement. [Remittance support](https://support.shiprocket.in/support/solutions/articles/43000463560-how-soon-can-i-receive-my-cod-amount-in-my-bank-account-) | Public help states transfer within 48 hours after delivery, requiring correct bank details and positive wallet balance; a negative balance defers it. Confirm contractual holidays/cut-offs, holds and eligibility. This article was updated in 2023, so treat it as a claim to verify in the current agreement. [COD remittance](https://help.delhivery.com/home/docs/cod-remittance) |
| Serviceability | API exposes courier serviceability; test each origin/destination and prepaid/COD combination with actual parcel details. [API](https://apidocs.shiprocket.in/?version=latest) | PIN API distinguishes prepaid/COD and other capabilities. Temporary non-serviceable responses must block dispatch. [B2C API FAQ](https://one.delhivery.com/developer-portal/document/b2c/detail/faq) |
| Sandbox and webhooks | Public API collection is available. A separate safe, no-charge sandbox was **not established** by this review; Postman examples are not proof of one. Tracking webhooks support a configurable security token, described as optional by the provider. Require authentication in Uyaras; do not assume HMAC signatures are supplied. Confirm replay/retry behavior and supplement with tracking reconciliation. [API](https://apidocs.shiprocket.in/?version=latest) | Client portal documents staging tests. Test credentials may require the account's business contact. Scan Push callbacks and tracking API are documented; missing scans require pulling tracking rather than assuming replay. Confirm authentication/signature and retry support during onboarding. [Developer portal](https://help.delhivery.com/docs/client-developer-portal-1), [FAQ](https://one.delhivery.com/developer-portal/document/b2c/detail/faq) |
| Labels/returns/refunds | Label-generation API returns a URL after AWB assignment; manifest generation has additional prerequisites. Shipping returns, shipping-credit adjustments and customer money refunds must remain separate workflows. [API](https://apidocs.shiprocket.in/?version=latest) | B2C APIs cover manifestation, cancellation, tracking, costs and labels. Reverse-pickup capability is PIN dependent. Customer refunds belong in the payment/manual-refund workflow, not a label operation. [API catalog](https://one.delhivery.com/developer-portal/documents/b2c/), [developer portal](https://help.delhivery.com/docs/client-developer-portal-1) |

No ranking of actual AP/Telangana delivery success or RTO rates is justified from these documents. National coverage claims do not establish a particular warehouse-to-customer lane.

## AP/Telangana verification before approval

The actual dispatch address, packed parcel measurements and allowed destination list are undecided. `520001` and `500001` in development are **test fixtures, not verified carrier coverage**. No authenticated PIN lookup was performed.

Once those inputs exist, create a comparison sheet for each candidate containing origin PIN, destination PIN, surface/express availability, prepaid availability, COD availability/limit, reverse pickup, quoted transit time, forward charge, COD charge, RTO charge, reverse charge and tax. Test metro, non-metro and rural lanes that the owner actually intends to serve. Record quote date and provider response. Recheck serviceability before shipment creation; checkout eligibility should combine Uyaras rules with current provider capability.

## Integration acceptance after provider approval

Each selected adapter must have local contract tests first, then documented sandbox evidence:

1. Server-calculated payment amount; success/failure/user-abandonment; status lookup after uncertain timeouts.
2. Authenticated webhook handling; duplicate and out-of-order events; late capture after reservation expiry; durable event IDs and reconciliation.
3. Full/partial refund initiation, pending/failure/success transitions, repeated request safety and refund-to-payment reference.
4. Serviceable and blocked PINs; COD disabled by PIN/product/order limit; shipment retry without duplicate booking; printable label; cancellation before/after handover.
5. Delivered, failed attempt and RTO events; returned-stock inspection; collected COD versus bank-remitted COD, with AWB, remittance and bank references.
6. Provider outage/retry handling and operational alerts. Sandbox results must be labelled simulated; actual carrier pickup and bank settlement require a later controlled live acceptance check.

Keep notification outbox events channel-agnostic. Email is the V1 delivery channel; a later phone/WhatsApp COD-confirmation workflow can consume the same order events without making courier delivery equivalent to customer payment or bank remittance.

## Decisions still required

- Owner approval of the payment and shipping candidates before integration.
- Actual pickup PIN/address, destination launch list and packed weights/dimensions.
- Confirmed account pricing, API entitlement, KYC readiness, COD remittance agreement and webhook test access.
- Approval of the chosen temporary public webhook endpoint when sandbox work starts. A tunnel is a test endpoint, not production hosting.

Until these are resolved, complete provider-independent features with mocks and keep real ordering disabled.

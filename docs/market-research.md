# Uyaras: India/AP launch assumptions

Research date: **21 November 2026**. This is a small first-party website comparison, not a survey of Andhra Pradesh demand or a validated business forecast. Prices and policies can change; promotional prices do not establish Uyaras's margins. All proposed values below are **editable test assumptions**, not approved production terms.

## What comparable stores show

| First-party source | Observed examples | Implication for Uyaras |
| --- | --- | --- |
| [Bewakoof plain women's T-shirts](https://www.bewakoof.com/women-plain-t-shirts) | Several plain tees listed at ₹499; oversized examples ₹599–649. The page advertises free shipping above ₹399. | A ₹499–699 sample range is a reasonable interface-testing choice; final prices require actual garment, packing, fulfilment, tax and return costs. |
| [Bonkers Corner T-shirts](https://www.bonkerscorner.com/collections/t-shirts) | Premium oversized examples listed at ₹899–999. | Premium fits/fabrics can occupy a higher price band; do not imply the sample Uyaras garments have those specifications. |
| [The Souled Store FAQ](https://www.thesouledstore.com/faqs) | General policy lists 30-day returns/exchanges, ₹50 delivery below ₹499 for non-members, COD ₹29 and a ₹4,000 COD maximum. COD is unavailable for some PINs. Separate sale restrictions apply. | Shipping, COD, return windows and exceptions belong in configuration and should be visible before order confirmation. |
| [Bonkers shipping policy](https://www.bonkerscorner.com/policies/shipping-policy) | ₹50 prepaid shipping and ₹90 COD shipping; stated delivery estimates vary between metros and other locations. | COD costs can be represented separately from delivery charges; a destination-specific estimate is preferable to a universal promise. |
| [Bonkers refund policy](https://www.bonkerscorner.com/policies/refund-policy) | General non-sale return window is 15 days, with original-condition/tag requirements; ₹100 reverse pickup charge and gift-card refunds are described. | Stores use materially different terms. Uyaras should publish its own approved policy rather than copying a competitor's restrictions. |

The product pages use sizes, fit information, filters and delivery checks. Bewakoof's [product page](https://www.bewakoof.com/p/105) asks for a delivery PIN. These support providing clear size guides and PIN-based estimates in V1. No competitor photographs, branding, reviews or “people bought this” counters should be copied into Uyaras.

## Proposed configurable demo rules

These are product decisions inferred from the comparison, **not market facts or shipping quotations**. The implementation report should identify any final demo values that differ.

| Setting | Proposed demo value | Production activation requirement |
| --- | --- | --- |
| Brand | Uyaras; calm blue, clean wordmark and readable typography | Owner reviews identity; no copied song art or lyrics |
| Catalog | Men's and women's T-shirts; sample price points ₹499, ₹599, ₹699 | Actual materials, dimensions, supplier costs, photos and prices entered |
| Images | Existing project sample images, clearly labelled as previews | Replace with owned/licensed photos of the actual stock |
| Delivery charge | ₹49; free when discounted merchandise subtotal is at least ₹999 | Confirm carrier/package economics; exclude COD fee from threshold |
| COD | Demo enabled only on explicit test PIN rules; ₹39 surcharge; total payable at most ₹3,000 | Confirm provider COD support, remittance charges, fraud/RTO controls and actual supported destinations |
| Delivery estimates | Editable per PIN; demo 4–7 business days, clearly a sample estimate | Actual pickup address, dispatch SLA and provider route estimates |
| Returns/exchanges | Request within 14 days after delivery; manual approval and inspection; size exchange only if stock exists | Owner approves policy and operating costs; preserve applicable customer rights |
| Refunds | Manual record with amount, reason and reference; no automatic transfer implied | Selected payment provider, authorized operator and confirmed process |
| Cancellation | Customer cancellation before dispatch; paid cancellation enters refund review | Owner approves rules; avoid promising an instant bank refund |
| Promotions | Configurable percentage/fixed discounts with expiry, minimum spend, cap and redemption limits | Margin review and published campaign terms |
| Warehouse/support | Empty or explicit “not configured”; never fabricated address, phone or mailbox | Real dispatch/return address and monitored support contact |
| Real inventory / ordering | Zero real stock; production ordering disabled | Verified stock entered and launch checks completed |

Defective/wrong-item handling should be a separate staff-reviewed reason, not silently rejected by ordinary change-of-mind restrictions. Return acceptance, inspection/restock and money refund must be separate recorded actions. A size exchange needs an explicit replacement allocation; a returned unit is not sellable until inspected. These are proposed operational safeguards rather than claims about the surveyed brands.

## AP and Telangana serviceability

Do not enable every PIN beginning with 5, or infer serviceability merely from the state name. As an example of the information a shipping adapter needs, [Shiprocket's official serviceability API](https://apidocs.shiprocket.in/?version=latest) takes pickup and delivery PINs, plus order information or COD/weight, and returns courier availability and estimates. This source illustrates the contract; **Shiprocket is not a chosen provider**.

Keep a configurable allowlist for the mock. Any seeded AP/Telangana PIN entries are test cases, not verified courier coverage. Live activation requires the actual pickup PIN, package weight/dimensions, carrier coverage for prepaid and COD separately, reverse-pickup support, rates and exclusions. Unsupported destinations should receive an explicit unavailable response rather than a successful checkout.

## GST: verified background, unresolved business configuration

The government's [17 September 2025 textile reform factsheet](https://www.pib.gov.in/FactsheetDetails.aspx?ModuleId=16&id=150293&lang=1&reg=20) reports **5% for readymade garments up to ₹2,500 per piece**, replacing the earlier ₹1,000 threshold. The [government FAQ on the reform](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2163560&lang=1&reg=6) identifies 22 September 2025 as the effective date for these general changes. Do not reuse the old ₹1,000/12% split from legacy FAQs.

The [Department of Consumer Affairs notification FAQ](https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/Frequently_Asked_Questions_on_GST_Part-3_whatsnews.pdf) points to Notification 9/2025-Central Tax (Rate) as the replacement goods schedule. Its [CBIC notification link](https://taxinformation.cbic.gov.in/view-pdf/1010436/ENG/Notifications) returned an HTTP 502 during this research, so this note does not claim a complete review of all subsequent amendments or final classification.

For a mock below that value, a **5% inclusive-tax example** can exercise calculations, provided it is labelled provisional. Keep rate, inclusive/exclusive treatment and product classification configurable. Do not add tax a second time to a tax-inclusive displayed price. Production remains blocked pending confirmation of legal seller identity, registration/GSTIN where applicable, HSN, current effective rates, discount/shipping treatment, invoice requirements and intra/inter-state tax allocation. A demo number is not a determination of Uyaras's legal liability.

## Hosting and launch boundary

Use **₹1,500–₹3,000/month**, up to 10,000 visits and 500 orders/month as planning assumptions supplied in the project discussion. This is not a priced hosting quote or a performance guarantee. Prefer independently deployable Next.js frontend, conventional FastAPI service, managed PostgreSQL and Cloudflare DNS/CDN/R2. Providers, domains, accounts, paid resources and deployment remain unselected.

Before accepting real orders: enter actual stock and catalog; approve tax/prices/policies; configure real support and dispatch details; verify AP/Telangana route coverage; select and test payment/shipping providers; configure storage/notifications; verify backups, restore and operational ownership. Keep the production order gate closed until these are complete. Mock payment success, mock tracking and manually recorded refunds must remain visibly distinguishable from live money movement and carrier events.

# Implementation tickets
These are the original planning estimates. For implemented coverage and remaining gaps after the shared-store work, see [local release status](local-release.md). Tickets are not all production-complete merely because their local workflow now runs.

Engineering effort in focused person-days for one engineer familiar with the stack. Each range includes feature-level automated tests and review fixes. It excludes vendor onboarding, content creation, business approvals and time awaiting review. Dependencies are ticket IDs. These ranges are for estimating work, not delivery dates.

| ID | Phase / priority | Ticket and acceptance evidence | Depends on | Estimate |
|---|---|---|---|---:|
| F01 | 1 / P0 | API foundation, migration, local environment and CI. Clean PostgreSQL migrate, request ID/error envelope, readiness and category visibility tests. Started. | — | 2–3 |
| F02 | 1 / P0 | Registration, login, logout and password reset. Tests for token reuse, session rotation, generic reset response and CSRF. | F01 | 3–5 |
| F03 | 1 / P0 | Staff roles and audit events. Test customer ownership, forbidden staff writes and audited grant/revoke. | F02 | 2–4 |
| F04 | 1 / P0 | Deploy a test environment, configure redacted logs, secret injection, health alerts and database backups. Demonstrate restore and rollback. | F01, hosting | 2–4 |
| C01 | 2 / P0 | Admin category tree, collection, product drafts and publish/archive. Validate unique slugs, hierarchy cycles and invisible drafts. | F03 | 3–5 |
| C02 | 2 / P0 | Variants, SKUs, media and size guides. Reject duplicate combinations; enforce upload size/type, scoped object keys and alt text. | C01 | 3–5 |
| C03 | 2 / P0 | Stock balances, adjustments, reason and audit ledger. Reject negative availability and keep movement/balance in one transaction. | C02, F03 | 2–4 |
| S01 | 3 / P0 | Mobile-first home, navigation, collection and search. URL filters survive back navigation; verify keyboard/focus and empty results. | C01, C02 | 4–6 |
| S02 | 3 / P0 | Product detail, size/colour, size guide, PIN preview and cart. Unavailable combinations disabled; cart reprices on every edit. | C03, S01, D01 PIN rules | 3–5 |
| S03 | 3 / P0 | Customer account, saved addresses, guest cart merge at sign-in. Cross-user reads fail; saved selection survives sign-in. | F02, S01 | 2–4 |
| D01 | 4 / P0 | PIN rules, charges, tax and server quote. Test unsupported PIN, COD ceilings, expiry and price changes. PIN preview can ship ahead of S02. | C01, commercial rules | 3–5 |
| D02 | 4 / P0 | Order snapshots, idempotency, atomic stock holds and expiry. Two real PostgreSQL checkouts for the last unit yield exactly one order. | C03, D01, S03 | 4–6 |
| D03 | 4 / P0 | Prepaid hosted flow, signed webhook inbox, retries and reconciliation. Test invalid, duplicate, delayed and out-of-order events using sandbox fixtures. | D02, gateway | 4–7 |
| D04 | 4 / P0 | COD path, eligible PIN/value tests, collection and remittance ledger. Delivered, collected and remitted states independently visible. | D02 | 2–4 |
| O01 | 5 / P0 | Order console, shipment creation, tracking and carrier events. Exercise cancellation, failed delivery and RTO without double restocking. | D03, D04, carrier | 4–7 |
| O02 | 5 / P0 | Manual returns, partial refunds and reconciliation. Reject over-return/over-refund; keep reason, audit, inspection and payment references. | O01 | 3–5 |
| O03 | 5 / P0 | Customer order history, tracking, policy/contact pages and transactional confirmation. Verify own-order access and retry-safe notification. | O01, support content | 2–4 |
| Q01 | 6 / P0 | Exercise PRD §15 end-to-end, WCAG 2.2 AA shopping journeys, mobile performance budgets and security checks. Triage and rerun failures. | S02, O02, O03, F04 | 3–5 |
| Q02 | 6 / P0 | Operational rehearsal: inventory count, pilot PINs, failed payment, COD settlement, partial return, restore and sign-off checklist. | Q01, business owners | 2–3 |
| P101 | Post-launch / P1 | Coupon automation, notifications beyond launch, wishlist, analytics and improved search. Select by conversion and support evidence. | Q02 | Re-estimate per feature |
| P201 | Later / P2 | Reviews, loyalty, recommendations, native apps and multiple warehouses. Discovery only when demand justifies cost. | Usage evidence | Unestimated |

**Next engineering ticket:** finish F01 on real PostgreSQL, then F02 and F03. F04 can proceed in parallel once staging hosting is selected. D01's PIN rule slice is a cross-phase dependency that supports the Phase 3 product page.

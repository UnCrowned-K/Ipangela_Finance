# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Omitted: existing Flask codebase (Python, server-rendered Jinja templates, vanilla JS + CSS, a JSON-backed persistence layer, PuLP for integer linear programming).

## Users

Solo operators, freelancers, and small business owners (primarily in South Africa, working in Rands). They work alone or with a small team and have no finance staff: they are responsible for pricing decisions, billing, and record-keeping in one workflow.

## Product Purpose

Profit Optimizer makes a single continuous pipeline out of three jobs a small operator must otherwise juggle:
1. **Decide** — model profit as variables with costs and constraints, and let an integer linear programming solver find the profit-maximizing choice.
2. **Bill** — turn those decisions into professional, sequenced invoices that can be sent and paid.
3. **Record** — track income, expenses, transfers, accounts, and budgets to see whether the decisions are working.

Success means a user makes a concrete business decision the Optimizer recommended, invoices it, and sees it in their financial records.

## Positioning

A decision-support tool rather than a ledger: the optimization solver is the center of the product, with invoicing and bookkeeping orbiting it. Unbundling prices, costs, and constraints into "what should I do next" — not "what did I already do."

## Operating Context

- Web app opened in a desktop browser on an average laptop; also used on phones for quick checks and invoice handling.
- Users import/export optimizer variables and finance data as JSON/CSV, generate PDF invoices, and email invoices to clients.
- Money is handled in ZAR by default (displayed as "R0.00"); invoices additionally support USD, EUR, GBP, JPY, CAD, AUD, CHF.
- Data persists server-side per registered user (JSON-backed storage) with session auth and CSRF protection.

## Capabilities and Constraints

- **Optimizer**: ILP solve via PuLP/CBC; variables with lower/upper bounds, cost, profit, and multiplier; budget and capacity constraints; save/restore and export results; delete/clear/edit variables.
- **Invoices**: multi-currency, unlimited line items with quantity/price/discount/tax, sequential numbering `INV-YYYY-XXXXXX`, statuses (Draft, Sent, Paid, Overdue, Cancelled), PDF generation, email-to-client, client management, preview.
- **Finance**: accounts; income/expense/transfer transactions with categories and tags; budgets; reports; CSV export and import; optional subscription-account tier.
- **Finance accounting**: money position (the five questions — in, out, owed, owing, actually made); customer and supplier ledger with contacts, invoices, bills, partial settlement, write-offs and aging buckets; financial statements on both a cash and an accrual basis, plus balance sheet, cash flow and expense analysis.
- **Finance compliance**: South African business profile and structuring checklist; VAT, PAYE, UIF, SDL, provisional and income tax obligations with deadlines and statuses; payroll runs; ZAR default with a configurable financial year end (February default) and 15% VAT.
- **Finance planning**: records-completeness health score with named fixes; funding readiness across revenue, margin, current ratio, DSO, runway, stability and growth, separating blockers from warnings; forecast scenarios projected from the user's own recent averages.
- **Pages**: marketing home, about, contact; auth (register/login/logout); profile with settings.
- Technical: Flask + server-rendered Jinja templates, consolidated single `style.css`, shared `app.js`, dark mode, reduced-motion support, 236 automated tests.
- Undecided: no pricing/billing tiers, no team roles, no public API commitments were confirmed.

### Accounting basis

Documented deliberately, because these choices are visible to the user and will not agree with each other:

- Cash basis counts money that moved; accrual basis counts what was earned and incurred. Both are always shown together.
- Settling a customer invoice or supplier bill is tagged, and accrual figures count the invoice or bill rather than the payment, so nothing is counted twice.
- Owner equity is a balancing plug. Inventory, fixed assets and depreciation are not tracked.
- Opening cash is derived from closing cash, since dated historical account balances are not stored.
- Cost of sales is inferred from category names and can be overridden by recategorising.
- Tax, payroll and funding figures are planning estimates from the user's own records. They support professional advice; they do not replace SARS or an accountant's judgement, and the UI and API both say so.

## Brand Commitments

None binding. The incumbent identity is green-accented with the name "Ipangela"; the user confirmed the redesign has full freedom over name, palette, and typography. Product purpose, features, and content are preserved.

## Evidence on Hand

- README feature inventory.
- Working application: finance dashboard, optimizer, invoice generator, import/export flows.
- 236 passing tests covering finance logic, accounting and reporting, compliance, forecasting, the finance page markup and its JavaScript wiring, optimizer state, file operations, CSRF, security, page rendering, and validators.
- No testimonials, case studies, press, or user research; none should be fabricated.

## Product Principles

1. **Decide, then bill, then record** — every screen should tie numbers back to the next operator decision.
2. **Low ceremony** — solo operators get no onboarding baggage; data is saved automatically and reversibly wherever possible.
3. **One pipeline, consistent language** — variables, line items, and transactions share terminology and styling so the three jobs feel like one workflow.
4. **Trustworthy numbers** — constraints and breakdowns are visible, edits are recoverable, and money formatting is correct first.
5. **ZAR-first** — Rand conventions are the default scene; extra currencies are explicit extensions.

## Accessibility & Inclusion

Dark mode and a `prefers-reduced-motion` kill-switch are implemented; keyboard focus rings and ARIA dialog/status semantics are in place. No stricter standard was confirmed.
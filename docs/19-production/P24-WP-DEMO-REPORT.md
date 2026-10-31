# P24-WP — Offline Demo Telemetry Quarantine & Report

Task: `FIN-P24-WP-001`; state **IN_PROGRESS / CI pending**.  
Branch `test/FIN-P24-WP-001-demo-telemetry-quarantine`.  
Claim scope: `SCHEMA_AND_REFERENCE_METRICS_ONLY`.

## Purpose
Prepare an OFFLINE, privacy-safe schema and reporting route for future user-owned FIBO MetaTrader 5 and cTrader demo test output, and local Tabdeal Spot MOCK fixtures. No broker account has been opened or verified; this task only exercises synthetic inputs.

This implementation is **not a broker adapter** and does not connect to MT5 SDK, OAuth, exchanges, sockets, user email or external trade orders. Its output cannot grant Owner first-Live, production venue certification, official demo approval or G13.

## Files
- `config/production/p24-demo-report-policy.json`: exact immutable no-network, no credentials, account-unattested policy.
- `packages/production/demo_telemetry_quarantine.py`: strict allowlist on input fields, structured trace IDs, DEMO environment pin, explicit source provenance, exact timestamps, equity/balance/open-PnL reconciliation, trade/rejection counter monotonicity, integer money units, dynamic bool/number typing, **flow-adjusted-equity drawdown** and flow-adjusted PnL.
- `tests/p24/test_demo_telemetry_quarantine.py`: 46 explicit tests for source qualification, unknown fields/secret leakage, timestamp/tick consistency, forged LIVE modes, cash-flow metrics, HTML escaping and no Live upgrade.
- `scripts/ci/p24wp_evidence.py`: self-contained *fictional* fixed 3-snapshot fixture. Writes JSON evidence, CSV observations and escaped static HTML twice.
- `.github/workflows/p24-demo-report.yml`: independent pinned-action CI + byte-identical report replay. The required Governance workflow continues to gate PR.
- `contracts/tasks/FIN-P24-WP-001.json`: bounded work and safety/review requirements.

## Crucial interpretation
- `SYNTHETIC_FIXTURE` is not evidence of real broker performance.
- `USER_SUPPLIED_SANITIZED_DEMO` is **not** proof that the account is owned, broker-attested, full feed, complete positions or funds. Source attribution remains FALSE until a separate authorised process verifies it.
- The input field `external_flow_minor` is **cumulative net external cash flow since the first observation**, not a per-sample transfer. Flow-adjusted equity is current equity minus cumulative flow. The drawdown baseline uses **flow-adjusted equity**, not raw equity; this prevents a pure deposit or withdrawal from being misreported as trading performance or drawdown. Only a descriptive synthetic metric is produced; accurate time-weighted broker-verified returns and intra-sample risk remain unmeasured.
- Nonpositive flow-adjusted equity is rejected rather than producing invalid drawdown percentages. Five new tests (41–45) cover deposits, withdrawals, cumulative cash flows and type substitution.
- The flow-adjusted net P&L metric represents change in provided equity adjusted by *reported* external cash flows. It is **not** an independently audited return, a trade-level profit factor or predictive out-of-sample strategy performance.
- Input account/login IDs, credentials, passwords, OTP, keys, unknown nested data, arbitrary metadata, live accounts and positive auth scope are denied; user must never upload raw broker reports if they include private data. Scrub them on user-controlled device first.
- Quoted historical synthetic data and arbitrary test currencies do not establish broker-specific fee/swap, calendar, actual tick confidence, slippage or drawdown truth. All values carry their declared unit.
- No login, network, order, money, leverage-limit, reset or broker permission capability exists in the module.

## PR relationship / no overlapping writes
Separate files from pending WR #492 and WO #493. P24-A dossier, frozen roadmap, shared Current State and Task Catalog, main Governance workflow and P20 execution engine are unchanged. Do not claim independent A5/A8/A10 approval or merge without reviewer evidence and postmerge reconciliation.

## Criteria
- [ ] Required Governance SUCCESS and strict Pyright 0 error.
- [ ] Dedicated 40 privacy/metric tests PASS.
- [ ] Double-byte-identical JSON, HTML and CSV.
- [ ] Independent A5/A8/A10 check of provenance and no real money/authority.
- [ ] PR review and merge ordering coordinated with #492 and #493.
- [ ] Postmerge validation and governance status reconciliation before CANONICAL_COMPLETE.

## Hard stage boundaries
`PRE_FIRST_LIVE=0/9`, `P24_B=BLOCKED`, `P24_C..I=NOT_STARTED`, `G13=NOT_STARTED`, `FIRST_LIVE_OWNER_GATE=NOT_GRANTED`, `LIVE_TRADING=DISABLED`, `AUTO_TRADING=DISABLED`.

Reference evidence from fake sample is purely demonstration of the reporting pipeline.

## 2026-10-31 policy-lineage security hardening
Strict runtime verification now refuses a report evaluator whose in-memory policy ID was replaced after initialization; additional negative test #46. This secures synthetic evidence identity but does not provide broker attestation or Live permission.

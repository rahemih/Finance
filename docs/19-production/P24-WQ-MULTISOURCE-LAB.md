# P24-WQ — Offline Multi-Source Reference Analysis Lab (Dukascopy / Crypto / Visual)

Task contract: `FIN-P24-WQ-001`  
Scope: **SYNTHETIC_RESEARCH_ONLY**  
State: IMPLEMENTATION / CI + independent A5/A8/A10 review pending

## Owner-approved direction
Analyze global Forex and crypto prices independently, cross-check independent reference sources, and only compare conclusions with actual *venue-native* local prices before any future legitimate order submission. Dukascopy FX, Binance crypto **historical research label only** and TradingView **manual visual-only** are shortlisted by Owner; production eligibility and license are **NOT** established for an Iran resident.

## What this PR really implements
- A source registry of exactly 7 **synthetic** quote adapters:
  1. Dukascopy-labeled EURUSD synthetic OTC mid;
  2. independent-root synthetic EURUSD mid;
  3. FIBO synthetic venue EURUSD quote (NOT executable);
  4. Binance-labeled BTCUSDT historical reference fixture (NO API access);
  5. separate-origin synthetic BTCUSDT reference;
  6. independent synthetic USDTIRT conversion rate;
  7. Tabdeal synthetic BTCIRT spot destination quote.
- Strict `Decimal` bids/asks, source and instrument roles, timestamps, observed timestamps and unique SHA256 lineage, exact policy allowlist (network DISABLED, credential NONE, noncommercial data license unverified, no external orders).
- Uses existing `packages/data_quality/cross_provider.py` (P07) for *same-instrument* provider comparison, preserving explicit semantic families `FX_OTC_REF_MID` and `CRYPTO_SPOT_REF_MID`. Any divergence or insufficient independent provenance quarantines result.
- Crypto cross-venue comparison uses `BTCUSDT_reference × USDTIRT_reference`, then checks simulated BTCIRT venue price, instead of conflating USDT, USD and Iranian local money. Conversion is **non-executable indicative reference only**. Fees, funding availability, market depth, slippage, FX conversion rights and transferable inventory are NOT established.
- Forex broker quote comparison is only indicative; an OTC FX mid does not equal a broker executable bid/ask or global centralised Forex volume.
- Independent A5 `risk_veto` forces `QUARANTINED_NO_SIGNAL` on otherwise aligned synthetic data; **NOT** an A5 production sign-off.
- Persian RTL **static** HTML dashboard and JSON + CSV generated twice with byte-identical replay and SHA-256 evidence; no app, user data, API, live chart connection or trading permission.
- 48 authored unit/negative tests including stale/future/misaligned timestamps, fake data entitlement, provider-root and reused-lineage spoofing, float/Decimal and bool/int confusion, crossed/nonfinite quotes, crypto conversion, broker drift, P07 divergence and risk veto.
- Strict JSON policy identity on disk and at runtime.

## Why no live Dukascopy/Binance/TradingView connector?
- Dukascopy JForex historical API/market-data rights and Iran-resident access must be verified for precise intended data storage and use; **do not assume** live access or commercial license.
- Binance excludes Iran-resident account use; no authenticated Binance login, restricted endpoint access, geo-bypass, or production crypto benchmark assumed. Any public historical Binance Vision dataset has noncommercial license conditions that must be separately reviewed.
- TradingView's website data/alerts are not licensed as an automated execution or signal API on ordinary consumer terms; manual visual use only. For first-party website charts consider the separately open-source **Lightweight Charts**, using our own entitled data feed, in the distinct WEB-P0 implementation track.
- Future provider adapters may accept **properly licensed** historical data only in a separately governed implementation after eligibility and data-license review; this current lab refuses non-synthetic data deliberately.

## Existing components reused; non-overlapping PRs
- `ADR-0002-provider-portability-canonical-contracts.md` accepted architecture.
- `packages/contracts/market_data.py` preserves origin/time/schema principles; this test lab does not change it.
- `packages/data_quality/cross_provider.py` real P07 comparator used in code.
- Existing P05/P07/P20/P23 untouched. All WQ paths new, no path overlap with PR #492 WR, #493 WO, #494 WP, #496–498 WEB-P0.

## Validation and closure
- [ ] Dedicated `P24 Multisource Reference Lab` CI PASS, 48 tests and double replay.
- [ ] Full existing Governance workflow PASS at exact HEAD, strict Pyright 0/0, SBOM policy, regression.
- [ ] Independent A5, A8, A10 review verdict with evidence (not author self-approval).
- [ ] Coordinated merge order + lock release, postmerge Governance/Branch Hygiene and GitHub/Linear synchronization before task marked CANONICAL_COMPLETE.
- [ ] Production provider & data rights, Iran market access, demo/live broker and Owner approvals remain separate **hard blockers**.

## Immutable production state
`PRE_FIRST_LIVE=0/9`, `P24-A=CANONICAL_COMPLETE`, `P24-B=BLOCKED`, `P24-C..I=NOT_STARTED`, `FIRST_LIVE_OWNER_GATE=NOT_GRANTED`, `G13=NOT_STARTED`, `LIVE/AUTO=DISABLED`.

No accounts, payments, KYC, secret, paid feed, external API/transaction or real profit was created or used.

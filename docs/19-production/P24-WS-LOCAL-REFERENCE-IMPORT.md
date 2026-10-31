# P24-WS — Local Reference CSV Import / License-Quarantined Data Intake

Task: `FIN-P24-WS-001`. Scope: **FILE_SCHEMA_AND_SYNTHETIC_REFERENCE_ONLY**. PR evidence not certified until latest-head CI and independent review.

## Motivation and source rights
The Owner wants to compare Forex references (such as Dukascopy) and crypto references (possibly Binance historical data) with separate sources, validate market symbols and FX conversion, visually review analysis with TradingView or an open-source own-data chart, and later use legally available local trading destinations. That plan DOES NOT grant provider data rights, user access to restricted brokers, automatic signals or real-money trading.

Official source constraints checked on 2026-10-31:
- Dukascopy JForex API: personal noncommercial by default, separate commercial agreement needed for product/service use: https://www.dukascopy.com/swiss/docs/api/index.php .
- CoinGecko **explicitly excludes Iran-resident counterparties**, as of Oct 2026; do not treat it as a verified replacement. https://support.coingecko.com/articles/1193865412-excluded-countries-list
- Kraken explicitly excludes Iran as a customer region. https://support.kraken.com/articles/where-is-kraken-licensed-or-regulated
- TradingView Lightweight Charts is Apache 2.0 library, charting only; market data must be separately licensed. https://www.tradingview.com/lightweight-charts/

No actual source API or commercial rights are assumed. Local user CSV is always marked **UNVERIFIED**; this lab cannot accept its arrival as a verified origin or rights to use commercially. Owner should not provide raw account statements, private personal information, keys or OTP; only quote-only sanitized CSV.

## Implementation
- `config/production/p24-local-reference-import-policy.json`: exact synthetic/unverified source policy, never network, secrets or trade rights.
- `packages/production/local_reference_import.py`: narrow CSV columns `event_time_ms,bid,ask`; source context identifies fixed MARKET/PAIR/ROLE and cadence; source files are hashed, bounded, UTF-8, timestamp-ordered, strictly positive finite Decimal bid/ask, non-crossed and checked for freshness when labelled RECENT_REFERENCE.
- Source identities `FX_REFERENCE_CANDIDATE EURUSD`, `CRYPTO_REFERENCE_CANDIDATE BTCUSDT`, `USDTIRT_REFERENCE_CANDIDATE USDTIRT` are only candidate labels. Import never claims independent source roots, valid license or executable prices.
- `OWNER_SUPPLIED_UNATTESTED` input may generate **QUARANTINED_UNATTESTED_SOURCE** evidence and sanitized display only, NOT a provider-attested live feed, P07 trusted input, strategy signal or order. `SYNTHETIC_FIXTURE` is a lab reference only.
- `tests/p24/test_local_reference_import.py`: **48 written unit/negative tests** for privacy, header/unknown fields, secrets, source modes, timeliness, quote integrity, byte deterministic replay and output escaping.
- `scripts/ci/p24ws_evidence.py`: synthetic CSV fixture (no external market quotes) and deterministic JSON, CSV and Persian HTML evidence.
- `.github/workflows/p24-local-reference-import.yml`: scoped CI with zero persisted Git credentials, double replay and 7-day artifact. Existing full Governance check remains mandatory.

## Legitimate next phases (not implemented)
1. Identify at least two truly independent vendors that permit this Iran-resident use and the expected purpose, clarify service rights and cost. Do not mistake public URLs for permission.
2. Ask Owner for contractual/logged proof if necessary; do not store KYC secrets in GitHub.
3. Only under a separate authenticated/authorized connector contract introduce network calls and validate time/lineage/accuracy/currency conversion against venue-side quotes. Do not permit source=unverified to issue trade signals.
4. Work with WEB-P0 owners to display the sanitized source/provenance matrix, not an unlicensed TradingView datafeed.

## Governance
No changes to P24-A, frozen P24 roadmap, P20–P23 shared contracts, PR #492–#494, #499 or WEB-P0. Dedicated high-risk A5/A8/A10 independent review and coordinated merge/postmerge CI/Branch Hygiene/Linear sync required. Do not claim CANONICAL_COMPLETE from successful branch CI alone.

`PRE_FIRST_LIVE=0/9`, `P24_B=BLOCKED`, `G13=NOT_STARTED`, `FIRST_LIVE_OWNER_GATE=NOT_GRANTED`, `LIVE/AUTO=DISABLED`.

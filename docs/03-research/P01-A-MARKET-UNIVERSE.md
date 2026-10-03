# P01-A — Market Universe & Instrument Taxonomy

STATE = RESEARCH_BASELINE  
TASK = `FIN-P01-WA-001`  
PHASE = `P01 — Market / Provider / Compliance Research`  
PROVIDER_SELECTION = `NOT_PERFORMED`  
BROKER_SELECTION = `NOT_PERFORMED`  
LIVE_TRADING = `DISABLED`

## 1. Objective

Define the provider-neutral identity model and initial candidate universe for Finance / NEXUS QUANT.

The intended **tradable** scope remains:
- Crypto
- Forex

The following remain **context markets by default**:
- Gold
- Oil
- U.S. dollar index
- Sovereign yields / bonds
- Equity indices
- Volatility
- selected commodities

A context instrument may later become tradable only through a governed roadmap change/provider/execution task. P01-A does not authorize that.

## 2. Design principles

### Canonical identity is not a provider symbol

Provider aliases such as `BTC-USD`, `XBT/USD`, `BTCUSDT`, `EUR_USD` or `GC` must map to a canonical identity. They never become the project-wide primary key by themselves.

### Instrument type is part of identity

The following are different instruments even when they reference the same economic asset:
- spot;
- perpetual futures;
- dated futures;
- index/benchmark;
- yield/rate series;
- proxy/derived series.

### Venue and settlement are explicit

For crypto derivatives, record:
- venue;
- contract type;
- quote currency;
- settlement currency;
- collateral currency;
- linear/inverse structure;
- expiry or perpetual status;
- funding rule;
- multiplier / contract size.

For Forex, record:
- OTC/broker/ECN/futures-proxy source class;
- price source;
- session/timezone assumptions;
- volume-source class and coverage confidence.

### Context and tradability are separate

The system may ingest a context instrument without allowing an order to be generated for it.

## 3. Canonical instrument model

Every normalized instrument registry entry must support these fields:

| Field | Meaning |
|---|---|
| `canonical_id` | Stable provider-neutral project ID |
| `asset_class` | crypto, forex, commodity, rates, equity_index, volatility, fx_index |
| `role` | tradable_candidate or context_only |
| `instrument_type` | spot, spot_otc, perpetual, futures, index, yield |
| `base` | base asset/currency when applicable |
| `quote` | quote asset/currency when applicable |
| `benchmark` | benchmark name where applicable |
| `venue_scope` | provider_neutral or named benchmark venue |
| `settlement_currency` | settlement unit or TBD_BY_VENUE |
| `collateral_currency` | derivatives collateral or TBD_BY_VENUE |
| `contract_multiplier` | contract size/multiplier when relevant |
| `expiry_model` | none, perpetual, dated |
| `trading_hours_model` | 24x7, OTC_24x5, exchange_calendar, source_calendar |
| `price_source_class` | spot venue, broker, exchange futures, official index, official rate |
| `volume_source_class` | centralized actual, broker/tick proxy, futures proxy, none |
| `volume_coverage_confidence` | high/medium/low/not_applicable; derived only from documented coverage |
| `chain_context` | chain/network identity when relevant |
| `provider_aliases` | per-provider symbols; populated later |
| `eligibility_tier` | CORE, RESEARCH, EXPANSION_DYNAMIC, CONTEXT |
| `status` | candidate, active_research, deferred, rejected, retired |
| `source_refs` | official/primary source references supporting identity |
| `notes` | limitations and interpretation rules |

## 4. Crypto candidate universe

### CORE bootstrap candidates

P01-A starts with two crypto anchors:

- **Bitcoin (BTC)**
  - spot candidate: `CRYPTO:BTC/USD:SPOT`
  - perpetual template: `CRYPTO:BTC/USD:PERP:LINEAR`
- **Ether (ETH)**
  - spot candidate: `CRYPTO:ETH/USD:SPOT`
  - perpetual template: `CRYPTO:ETH/USD:PERP:LINEAR`

Why only BTC/ETH at bootstrap:
- they provide a minimal, interpretable universe for validating provider coverage, spot/perpetual semantics, funding, order book and execution contracts;
- CME maintains Bitcoin and Ether futures product families, supporting their role as major benchmark crypto assets;
- official Coinbase instrument documentation demonstrates the important distinction between `SPOT` and `PERP`, and shows BTC/ETH perpetual examples;
- expansion should follow measured liquidity, data quality, venue coverage and compliance rather than a static altcoin list.

This is **not** an investment ranking or claim that BTC/ETH have higher future returns.

### Crypto expansion

Other crypto assets enter `EXPANSION_DYNAMIC` only after P01-B/P01-C evidence confirms:
- adequate real-time and historical market data;
- multiple eligible venues or a justified single-venue case;
- reliable order book/trade/funding/open-interest data when required;
- acceptable spread/depth/turnover;
- stable instrument metadata;
- legal/regional eligibility;
- operationally acceptable symbol/contract behavior.

Numeric admission thresholds remain **TBD** until provider data are evaluated. P01-A deliberately does not invent thresholds.

### Chain identity

Trade identity and chain identity are related but not interchangeable.

Example:
- ETH asset may trade on centralized venues independent of on-chain settlement activity.
- Blockscout live registry verification identified Ethereum mainnet as chain ID `1`, native currency `ETH`.
- chain metadata is stored as context/provenance, not as a substitute for venue instrument identity.

## 5. Forex candidate universe

The Forex market is decentralized/OTC. The project must not imply that one broker, ECN, tick feed or futures venue represents consolidated global Spot FX volume.

The BIS 2025 Triennial Survey reports that the U.S. dollar was on one side of 89.2% of FX trades in April 2025 and that all top 10 currency pairs involved USD. This supports a USD-centered bootstrap universe.

### CORE FX candidates

- `FX:EUR/USD:SPOT_OTC`
- `FX:USD/JPY:SPOT_OTC`
- `FX:GBP/USD:SPOT_OTC`
- `FX:AUD/USD:SPOT_OTC`
- `FX:USD/CAD:SPOT_OTC`
- `FX:USD/CHF:SPOT_OTC`
- `FX:NZD/USD:SPOT_OTC`

These are a research baseline, not a broker-selection or return ranking.

### RESEARCH FX candidates

Crosses:
- `FX:EUR/GBP:SPOT_OTC`
- `FX:EUR/JPY:SPOT_OTC`
- `FX:GBP/JPY:SPOT_OTC`

Additional USD pairs for provider/compliance review:
- USD/CNY and/or USD/CNH — **must not be conflated**; onshore/offshore market conventions require explicit metadata.
- USD/HKD
- USD/SGD
- USD/MXN

Research-tier pairs do not become active merely because data exist.

### Mandatory Forex volume labeling

Every Forex volume/order-flow feature must declare one of:
- `BROKER_VOLUME_PROXY`
- `TICK_VOLUME_PROXY`
- `ECN_VOLUME_PROXY`
- `FUTURES_VOLUME_PROXY`
- `AGGREGATED_PROXY`

and include:
- provider/venue;
- coverage period;
- coverage universe;
- confidence;
- known blind spots.

The label `GLOBAL_SPOT_FX_VOLUME` is forbidden unless a future source can genuinely substantiate that claim.

## 6. Context universe

Context instruments are ingested to help regime, intermarket, macro, liquidity and risk interpretation. They are **not tradable by default** in NEXUS QUANT.

### Gold

Primary context identities:
- `COMMODITY:XAU/USD:SPOT_OTC` — OTC spot-price context; volume requires proxy labeling.
- `COMMODITY:GOLD:GC:FUTURES:COMEX` — centralized futures benchmark context.

CME official documentation identifies GC Gold futures as a leading benchmark futures contract; the standard contract represents 100 troy ounces and is quoted in U.S. dollars/cents per troy ounce.

### Oil

- `COMMODITY:WTI:CL:FUTURES:NYMEX`
- `COMMODITY:BRENT:B:FUTURES:ICE_EUROPE`

CME/NYMEX rules define Light Sweet Crude Oil futures with delivery in Cushing, Oklahoma and a 1,000-barrel trading unit. ICE defines Brent Crude Futures as a deliverable EFP-based contract with an option to cash settle against the ICE Brent Index.

### U.S. Dollar Index

- `FX_INDEX:USDX:DX:FUTURES:ICE_US`
- optional index-level normalized series: `FX_INDEX:USDX:INDEX`

ICE identifies USDX futures symbol `DX` and describes USDX as a benchmark for the international value of the U.S. dollar relative to a basket of currencies.

### U.S. Treasury rates

Minimum curve context:
- `RATES:UST:CMT:2Y`
- `RATES:UST:CMT:10Y`
- derived spread: `RATES:UST:CMT:10Y-2Y`

The U.S. Treasury states that par yield curve / Constant Maturity Treasury values are read from its official curve at fixed maturities including 2 and 10 years.

Later expansion may include 3M, 1Y, 5Y, 30Y and real-yield series.

### Equity indices

Baseline context entities:
- `EQUITY_INDEX:SPX:INDEX`
- `EQUITY_INDEX:NDX:INDEX`

Provider/licensing and redistribution rights remain a P01-B/P01-E concern. Index data cannot be assumed freely redistributable.

### Volatility

- `VOLATILITY:VIX:INDEX`

Cboe defines VIX as a measure of market expectations of 30-day forward-looking U.S. equity volatility conveyed by S&P 500 option prices.

## 7. Universe eligibility state machine

An instrument moves through:

`DISCOVERED → RESEARCH_CANDIDATE → DATA_ELIGIBLE → COMPLIANCE_ELIGIBLE → ARCHITECTURE_SUPPORTED → DEMO_ELIGIBLE → SHADOW_ELIGIBLE → LIVE_ELIGIBLE`

Important:
- P01-A can only assign `RESEARCH_CANDIDATE`.
- P01-B/P01-C/P01-D determine provider/broker/compliance evidence.
- later gates determine Demo/Shadow/Live eligibility.
- `LIVE_ELIGIBLE` still does not mean a position should be opened; signal/risk/firewall/execution gates remain independent.

## 8. Expansion eligibility dimensions

No single volume number decides eligibility. Later provider research must score:

### Data
- real-time trades/quotes;
- order book depth where needed;
- historical depth;
- funding/open interest/liquidations for crypto derivatives;
- timestamps/sequence IDs;
- symbol/contract metadata;
- revision/change history;
- rate-limit/capacity behavior.

### Market quality
- spread distribution;
- depth near mid;
- turnover;
- gap frequency;
- price continuity;
- venue concentration;
- liquidation/crowding characteristics where applicable.

### Operations
- API stability;
- maintenance visibility;
- reconnect behavior;
- sandbox/test support;
- supportability;
- fallback source.

### Compliance / rights
- jurisdiction eligibility;
- data storage rights;
- redistribution/display rights;
- professional/non-professional classification where relevant;
- broker/exchange account constraints.

## 9. Symbol normalization rules

Examples:

| External form | Canonical concept |
|---|---|
| `EURUSD`, `EUR_USD`, `EUR/USD` | `FX:EUR/USD:SPOT_OTC` |
| `BTC-USD`, `XBT/USD` | `CRYPTO:BTC/USD:SPOT` after provider-specific asset alias mapping |
| `BTC-PERP`, `BTCUSDT-PERP` | never collapsed without quote/settlement/linear-vs-inverse checks |
| `GC` | `COMMODITY:GOLD:GC:FUTURES:COMEX` only when venue/product context proves GC means that contract |
| `CL` | `COMMODITY:WTI:CL:FUTURES:NYMEX` only with venue/product context |
| `DX` | `FX_INDEX:USDX:DX:FUTURES:ICE_US` only with ICE product context |

Symbol aliases are namespaced by provider/venue to prevent collisions.

## 10. Session model

- Crypto spot/perpetual: generally modeled as `24x7`, but provider maintenance/outage windows remain source-specific.
- Spot FX: modeled as `OTC_24x5` with explicit session calendar and weekend closure semantics; exact provider week/session boundaries are adapter metadata.
- Exchange futures/index products: use the official exchange/product calendar.
- Official rates/macro context: use source publication calendar, not a trading-hours model.

DST handling must use IANA time zones rather than fixed UTC offsets when a venue/source publishes local-time schedules.

## 11. Source register

Primary/current sources used in this task:

1. BIS — 2025 Triennial Central Bank Survey, OTC FX turnover:
   - https://www.bis.org/statistics/rpfx25_fx.htm
   - supports FX structure, USD dominance and pair/currency research rationale.
2. CME Group — Gold Futures:
   - https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html
3. CME/NYMEX — Light Sweet Crude Oil futures rules / WTI:
   - https://www.cmegroup.com/rulebook/NYMEX/2/200.pdf
   - https://www.cmegroup.com/markets/energy/wti-crude-oil-futures.html
4. ICE — Brent Crude Futures:
   - https://www.ice.com/products/219
5. ICE — U.S. Dollar Index futures:
   - https://www.ice.com/forex/usdx
6. U.S. Department of the Treasury — Daily Treasury Par Yield Curve Rates:
   - https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=2026&type=daily_treasury_yield_curve
7. Cboe — VIX:
   - https://www.cboe.com/tradable-products/vix/
   - https://cdn.cboe.com/resources/indices/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf
8. CME Group — Cryptocurrency Futures:
   - https://www.cmegroup.com/markets/cryptocurrencies/cryptocurrency-futures.html
9. Coinbase International Exchange — instrument concepts/product specifications:
   - https://docs.cdp.coinbase.com/international-exchange/concepts/instruments
   - used only as an example of spot/perpetual instrument semantics, **not** as provider selection.
10. Blockscout live chain registry:
   - Ethereum mainnet = chain ID `1`, native currency `ETH`, verified during task execution.

## 12. Limitations / next workstreams

P01-A intentionally does not decide:
- which data vendor is primary/backup;
- which broker/exchange is eligible;
- legal eligibility in any owner jurisdiction;
- numeric liquidity thresholds;
- subscription/licensing economics;
- exact provider aliases;
- production trading instruments.

Those move to:
- P01-B Market Data Provider Inventory;
- P01-C Broker / Exchange Inventory;
- P01-D Jurisdiction & Compliance;
- P01-E Cost / Licensing / Data Rights;
- P01-F Primary / Backup Provider Strategy;
- P01-G Provider Baseline Decision.

## 13. P01-A proposed result

Provider-neutral taxonomy: `READY_FOR_CANONICAL_REVIEW`  
Bootstrap tradable research candidates: BTC, ETH + seven major FX pairs  
Context baseline: Gold, WTI, Brent, USDX, UST 2Y/10Y, SPX, NDX, VIX  
Production provider: `NOT_SELECTED`  
Broker/exchange: `NOT_SELECTED`  
Live trading: `DISABLED`

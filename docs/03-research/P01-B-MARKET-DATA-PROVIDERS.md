# P01-B — Market Data Provider Inventory & Scorecards

STATE = RESEARCH_BASELINE  
TASK = `FIN-P01-WB-001`  
PHASE = `P01 — Market / Provider / Compliance Research`  
PRODUCTION_PROVIDER_SELECTION = `NOT_PERFORMED`  
BROKER_SELECTION = `NOT_PERFORMED`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Objective

Inventory and compare candidate market-data sources that could later support the canonical P01-A universe.

P01-B is **research only**. It does not:
- buy or activate a commercial subscription;
- create credentials;
- implement an adapter;
- select a production primary/backup provider;
- select a broker/exchange;
- enable Demo, Shadow, Live or Auto Trading.

The purpose is to reduce uncertainty before P01-D/E/F/G make compliance, cost, fallback and baseline decisions.

## 2. Research rules

### Official-first

Provider claims are grounded in official provider documentation, pricing, terms or product pages where available.

Exa is used only to discover and retrieve supporting provider documentation. Search results do not override official terms.

### Unknown stays unknown

If a provider does not publish a specific limit, SLA, redistribution right, exact historical depth or commercial entitlement, this document records `UNKNOWN / CONTRACT REVIEW` rather than inventing a value.

### Technical access is not legal entitlement

An endpoint being technically available does not prove that:
- internal non-display use is licensed;
- redistribution/display is licensed;
- derived-data use is licensed;
- exchange/index entitlements are covered;
- automated trading use is permitted.

Those questions continue into P01-D and P01-E.

### Forex volume remains proxy-labeled

No vendor is allowed to convert OTC Forex into a fictional centralized global volume feed.

Every Spot FX volume/order-flow field later must retain one of:
- `BROKER_VOLUME_PROXY`
- `TICK_VOLUME_PROXY`
- `ECN_VOLUME_PROXY`
- `FUTURES_VOLUME_PROXY`
- `AGGREGATED_PROXY`

with provider/venue, coverage, confidence and blind spots.

## 3. Evaluation dimensions

P01-B does not produce a winner. It records evidence across:

1. Market coverage
2. Real-time delivery
3. Historical depth/replay
4. L1/L2/L3/order-book suitability
5. Crypto derivatives metrics
6. Forex quote semantics
7. Context market coverage
8. Timestamp/provenance quality
9. API/stream operational limits
10. Licensing/redistribution clarity
11. SLA/support evidence
12. Cost transparency
13. Suitability for independent cross-validation
14. Fit with future primary/backup design

Machine-readable evidence lives in:

`docs/03-research/p01-b-provider-scorecards.json`

## 4. Candidate provider inventory

### 4.1 Databento

**Class:** exchange-market-data vendor

**Documented strengths**
- unified live and historical APIs;
- futures/options/equities coverage;
- CME/CBOT/NYMEX/COMEX coverage documented publicly;
- L1/L2/L3-style schemas including trades, MBP and MBO;
- long historical depth on supported datasets;
- raw TCP + HTTP and official client libraries;
- nanosecond/PTP timestamp claims and multiple event timestamps;
- public usage/licensing pricing model.

**Likely role in Finance**
- centralized futures context;
- Gold/WTI/CME crypto futures;
- replay/backtest source;
- independent cross-validation.

**Limitations / open items**
- not a complete Spot FX + crypto spot solution for our target scope;
- exact exchange entitlements for every desired context market need contract review;
- exact L2/L3 history cost and production support tier remain commercial questions.

**Public evidence**
- https://databento.com/pricing
- https://databento.com/live

### 4.2 dxFeed

**Class:** multi-asset market-data vendor

**Documented strengths**
- global equities, futures, options, indices, Forex and crypto coverage;
- real-time, delayed, replay and historical delivery;
- Java/C++/.NET/JavaScript/Go/Swift plus REST/WebSocket/FIX;
- normalized multi-feed access;
- formal exchange/data-originator entitlement model.

**Likely role**
- broad multi-asset candidate;
- Forex reference candidate;
- context-market source;
- independent cross-validation.

**Important licensing finding**
dxFeed terms state that data-originator requirements apply, and redistribution/third-party/derived use may require prior authorization.

**Open items**
- exact Spot FX contributor set and liquidity/depth semantics;
- production rate/capacity limits;
- SLA;
- full target-set entitlement costs.

**Public evidence**
- https://kb.dxfeed.com/en/market-data-api.html
- https://dxfeed.com/coverage/global/
- https://dxfeed.com/tr/general-terms-and-conditions-for-services/

### 4.3 Twelve Data

**Class:** multi-asset API vendor

**Documented strengths**
- Forex, crypto, equities, commodities, ETFs and other markets through REST and WebSocket;
- time-series/history endpoints;
- daily-updated symbol/reference endpoints;
- explicit API-credit and WebSocket-credit model;
- documented 429 behavior and connection/credit semantics;
- transparent individual pricing.

**Operational evidence**
Twelve Data documents per-minute API credits, WebSocket subscription credits and a default limit of three WebSocket connections in its support material.

**Likely role**
- lower-complexity Forex/crypto reference;
- broad context/reference data;
- secondary validation.

**Limitations**
- deep L2/L3 suitability for order-flow work is not established by the evidence gathered here;
- index licensing and commercial non-display rights need contract review;
- tick-history depth must be verified for the exact plan/market.

**Public evidence**
- https://twelvedata.com/docs
- https://support.twelvedata.com/en/articles/5615854-credits
- https://twelvedata.com/pricing

### 4.4 Massive

**Class:** multi-asset API vendor

**Documented strengths**
- real-time WebSocket Forex BBO quotes;
- Forex per-second/per-minute aggregates;
- crypto live aggregates/trades/quotes;
- index values and aggregates;
- REST + WebSocket product model;
- public pricing page.

**Critical Forex interpretation**
Massive's Forex aggregate documentation says aggregates are derived from best bid/offer quotes rather than executed trades. Therefore any “volume” exposed there must remain proxy-labeled in Finance and must not be treated as global executed Spot FX volume.

**Likely role**
- Forex quote/reference source;
- crypto reference source;
- index context;
- secondary validation.

**Open items**
- deep order-book/history requirements;
- exact index entitlements;
- production limits/SLA;
- commercial non-display/redistribution terms.

**Public evidence**
- https://massive.com/pricing
- https://massive.com/docs/websocket/forex/quotes
- https://massive.com/docs/websocket/forex/aggregates-per-second
- https://massive.com/docs/websocket/crypto/aggregates-per-second
- https://massive.com/docs/websocket/indices/aggregates-per-second

### 4.5 Kaiko

**Class:** crypto-specialist market-data vendor

**Documented strengths**
- L1/L2 market data;
- trade, top-of-book and full depth products;
- real-time stream + REST + cloud delivery;
- historical/replay support;
- crypto derivatives pricing/reference metrics;
- exchange and collection timestamps;
- broad CeFi/DeFi-oriented institutional market-data stack;
- formal data licensing and documented redistribution relationships.

**Likely role**
- primary crypto-data candidate;
- crypto order-flow source;
- derivatives/funding/liquidity research;
- cross-provider validation.

**Commercial model**
Public Kaiko material describes custom enterprise plans depending on instruments, data type, granularity, historical/live access and usage.

**Licensing caution**
Kaiko distinguishes license/use cases such as display and other purposes. Entitlement must be mapped to Finance’s private, non-display automated analysis and later trading use.

**Open items**
- exact commercial quote;
- product-specific SLA;
- exact funding/OI/liquidation coverage by venue;
- contract rights for retention and derived features.

**Public evidence**
- https://docs.kaiko.com/explore-our-data/subscriptions-channel-availability
- https://docs.kaiko.com/stream/data-feeds/level-1-and-level-2-data/level-2-tick-level/bids-and-asks
- https://docs.kaiko.com/stream/data-feeds/reference-data/derivatives-pricing
- https://www.kaiko.com/about-kaiko/pricing-and-contracts
- https://www.kaiko.com/exchange-agreements

### 4.6 CoinAPI

**Class:** crypto-specialist aggregator

**Documented strengths**
- real-time and historical crypto market data;
- REST and WebSocket;
- trades, quotes and order-book streams;
- plan-specific request/data quotas;
- heartbeat/connectivity semantics;
- FIX availability on higher/add-on tiers;
- public pricing.

**Likely role**
- secondary crypto candidate;
- symbol/reference normalization input;
- cross-validation source.

**Open items**
- exact derivatives/funding/OI/liquidation coverage;
- historical L2 retention;
- commercial use/redistribution rights;
- enterprise SLA.

**Public evidence**
- https://www.coinapi.io/products/market-data-api/docs
- https://www.coinapi.io/products/market-data-api/docs/websocket
- https://www.coinapi.io/products/market-data-api/pricing

### 4.7 FRED / ALFRED

**Class:** official macro-data aggregation service

**Documented strengths**
- large macro/rates/economic-series catalog;
- API access;
- revision-aware real-time-period semantics;
- vintage-date retrieval through ALFRED/FRED API;
- suitable for reproducible macro event studies and “what was known then” analysis.

**Likely role**
- macro/rates context;
- vintage-aware backtesting;
- cross-check against original release agencies.

**Important legal limitation**
FRED states that third-party series may retain their own copyright/use restrictions; availability through FRED does not override those rights.

**Open items**
- series-by-series rights classification;
- which high-priority series should instead be ingested directly from BLS/BEA/CFTC/Treasury/Fed source endpoints.

**Public evidence**
- https://fred.stlouisfed.org/docs/api/fred/
- https://fred.stlouisfed.org/docs/api/fred/alfred.html
- https://fred.stlouisfed.org/docs/api/terms_of_use.html

### 4.8 Direct official / exchange sources

**Class:** direct exchange, benchmark and agency sources

Examples:
- CME
- ICE
- Cboe
- U.S. Treasury
- Federal Reserve/FRED/ALFRED
- BLS
- BEA
- CFTC

**Strength**
Authoritative definitions, schedules, benchmark values, releases and product metadata.

**Trade-off**
Direct-source use can increase:
- number of integrations;
- entitlement complexity;
- exchange/non-display fees;
- operational diversity;
- source-specific calendars and schemas.

Finance should prefer direct official sources for macro releases and benchmark definitions when practical, while using normalized vendors where operational cost and licensing are justified.

### 4.9 Blockscout

**Class:** supplemental on-chain source

Blockscout is useful for:
- EVM chain identity;
- transactions;
- contract/source metadata;
- token and network context;
- on-chain provenance.

It is **not** a replacement for exchange trades/order books/funding/open interest.

Potential role:
- on-chain context;
- chain metadata validation;
- later P10/P12 crypto intelligence.

Production rate limits, retention and selected-chain coverage remain future architecture/provider decisions.

## 5. Coverage view by project need

| Need | Strong documented candidates | Secondary / context candidates | Notes |
|---|---|---|---|
| Crypto spot/trades | Kaiko, CoinAPI | Massive, Twelve Data | Exchange-native feeds evaluated later with P01-C implications |
| Crypto L2/order book | Kaiko, CoinAPI | direct venue feeds | Exact history/retention matters |
| Crypto derivatives metrics | Kaiko | CoinAPI / direct venue | Venue-by-venue funding/OI/liquidation audit still required |
| Spot FX BBO/reference | dxFeed, Massive, Twelve Data | later broker/ECN feeds | No “global volume” assumption |
| Gold/WTI futures context | Databento / direct CME | dxFeed | Licensing/entitlements matter |
| Brent/USDX | direct ICE / eligible normalized vendor | dxFeed | Exchange licensing must be checked |
| SPX/NDX/VIX | direct/licensed index source, dxFeed | Massive where plan supports | Index entitlements/redistribution are sensitive |
| UST yields/macro | Treasury/FRED/ALFRED/direct agencies | vendor copies for validation | Vintage/revision handling mandatory |
| On-chain EVM context | Blockscout | later direct node/indexer | Not market-data replacement |

## 6. Provider role architecture emerging from P01-B

No provider is selected, but the evidence suggests the future design should **not** assume one vendor can satisfy every need equally well.

The architecture should preserve at least these logical source roles:

1. **Crypto microstructure source**
   - deep trades/order book/derivatives metrics.

2. **Forex quote/reference source**
   - BBO/quote history with explicit proxy semantics.

3. **Centralized futures/context source**
   - CME/ICE/Cboe/index/rates-related market context.

4. **Official macro source**
   - release data and vintages.

5. **Cross-validation source**
   - independent enough to detect stale/bad primary feed behavior.

6. **On-chain supplemental source**
   - network/contract/transaction evidence.

This is a design requirement for P01-F, not a provider decision.

## 7. Independence / fallback considerations

A “backup” is not independent if it ultimately republishes the same upstream source through the same infrastructure failure domain.

P01-F must assess:
- upstream venue/source independence;
- vendor infrastructure independence;
- cloud/region independence;
- normalization independence;
- timestamp provenance;
- symbol mapping independence;
- failure/reconnect semantics;
- license rights to retain both feeds concurrently.

Cross-provider differences should be observable rather than silently normalized away.

## 8. Licensing and data-rights flags carried forward

P01-E must resolve at least:

- internal display vs internal non-display use;
- automated analysis/trading usage;
- historical retention duration;
- derived features/models;
- redistribution to team dashboards;
- public display, if ever introduced;
- index-specific entitlements;
- exchange professional/non-professional status;
- cloud redistribution/pass-through;
- audit/reporting obligations;
- use of data in model training or stored research datasets.

No right is assumed merely because a public API or trial exists.

## 9. Operational validation required before P01-G

Shortlisted providers should later be tested in controlled trials for:

- disconnect/reconnect;
- sequence gaps;
- stale feed detection;
- timestamp skew;
- symbol-definition changes;
- DST/calendar behavior;
- rate-limit enforcement;
- burst behavior;
- batch/backfill speed;
- WebSocket resubscription;
- maintenance/outage notices;
- identical-event deduplication;
- cross-provider divergence;
- retention/replay reproducibility.

P01-B records public evidence only; it does not fabricate benchmark results.

## 10. Preliminary fit, not final selection

Based on documented capability **only**, the provider roles worth carrying into later P01 work are:

- **Crypto specialist:** Kaiko, CoinAPI
- **Broad multi-asset:** dxFeed, Twelve Data, Massive
- **Futures/deep centralized market data:** Databento + direct exchange feeds
- **Macro/vintages:** FRED/ALFRED + direct agencies
- **On-chain supplemental:** Blockscout

This is not a final ordering or procurement decision.

P01-D/E/F may materially change the viable set due to:
- jurisdiction;
- licensing;
- cost;
- retention rights;
- operational limits;
- independence/fallback requirements.

## 11. Source register

Checked 2026-10-03.

### Databento
- https://databento.com/pricing
- https://databento.com/live

### dxFeed
- https://kb.dxfeed.com/en/market-data-api.html
- https://dxfeed.com/coverage/global/
- https://dxfeed.com/tr/general-terms-and-conditions-for-services/

### Twelve Data
- https://twelvedata.com/docs
- https://support.twelvedata.com/en/articles/5615854-credits
- https://twelvedata.com/pricing

### Massive
- https://massive.com/pricing
- https://massive.com/docs/websocket/forex/quotes
- https://massive.com/docs/websocket/forex/aggregates-per-second
- https://massive.com/docs/websocket/crypto/aggregates-per-second
- https://massive.com/docs/websocket/indices/aggregates-per-second

### Kaiko
- https://docs.kaiko.com/explore-our-data/subscriptions-channel-availability
- https://docs.kaiko.com/stream/data-feeds/level-1-and-level-2-data/level-2-tick-level/bids-and-asks
- https://docs.kaiko.com/stream/data-feeds/reference-data/derivatives-pricing
- https://www.kaiko.com/about-kaiko/pricing-and-contracts
- https://www.kaiko.com/exchange-agreements

### CoinAPI
- https://www.coinapi.io/products/market-data-api/docs
- https://www.coinapi.io/products/market-data-api/docs/websocket
- https://www.coinapi.io/products/market-data-api/pricing

### FRED / ALFRED
- https://fred.stlouisfed.org/docs/api/fred/
- https://fred.stlouisfed.org/docs/api/fred/alfred.html
- https://fred.stlouisfed.org/docs/api/terms_of_use.html

### Existing P01-A official sources
See `docs/03-research/P01-A-MARKET-UNIVERSE.md`.

## 12. P01-B result

Provider inventory = `READY_FOR_CANONICAL_REVIEW`  
Machine-readable scorecards = `CREATED`  
Production provider = `NOT_SELECTED`  
Primary/backup decision = `DEFERRED_TO_P01_F_G`  
Broker/exchange = `NOT_SELECTED`  
Credentials = `NONE`  
Live trading = `DISABLED`

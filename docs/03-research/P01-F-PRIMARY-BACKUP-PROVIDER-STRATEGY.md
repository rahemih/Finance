# P01-F — Primary / Backup Provider Strategy

STATE = STRATEGY_BASELINE  
TASK = `FIN-P01-WF-001`  
PHASE = `P01 — Market / Provider / Compliance Research`  
FINAL_PROVIDER_SELECTION = `NOT_PERFORMED`  
OWNER_JURISDICTION = `UNSET_HUMAN_GATE`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Objective

Define how NEXUS QUANT will avoid single-provider dependency while preserving source provenance, data quality, risk control and deterministic recovery.

P01-F decides the **redundancy architecture**, not the final vendor/broker.

The governing pattern is:

`Primary operational source → independent Backup → authoritative Cross-check`

where practical.

For execution, the pattern is intentionally different:

`Primary execution venue → halt/reconcile on uncertainty → controlled future-intent switch to certified backup`

There is no blind automatic live cross-broker replay.

## 2. Why one provider is not enough

The project spans domains with different market structures:

- Crypto spot/order book/perpetuals
- decentralized OTC Spot FX
- centralized futures and benchmark indices
- official macro/rates releases
- on-chain state

No single vendor is authoritative across all five.

A vendor can also fail through:
- network outage;
- upstream exchange outage;
- stale or partial data;
- schema change;
- entitlement expiry;
- normalization defect;
- rate limiting;
- legal/geographic restriction;
- commercial cancellation.

Therefore resilience must be domain-specific.

## 3. System states

Provider/data routing uses these conceptual states:

- `NORMAL`
- `PRIMARY_DEGRADED`
- `BACKUP_VALIDATING`
- `BACKUP_ACTIVE`
- `CROSSCHECK_DIVERGENCE`
- `FAIL_CLOSED`
- `RECOVERY_VALIDATION`

These are design states only in P01. Runtime implementation is deferred to P05/P07/P22.

## 4. Common health dimensions

Any future provider-health decision must consider more than "connection up/down".

Required dimensions:

- freshness;
- sequence/gap integrity;
- timestamp quality;
- latency distribution;
- completeness;
- schema-contract compliance;
- cross-provider price divergence;
- order-book consistency;
- provider service status;
- entitlement/licence validity;
- credential/session health where applicable.

## 5. Crypto market data strategy

### Preferred architecture

**Primary class:** normalized multi-venue specialist  
**Backup class:** independent normalized provider  
**Authoritative cross-check:** venue-native feed for the actual traded venue(s)

Conditional primary/backup candidates:
- Kaiko
- CoinAPI

Venue-native cross-check candidates:
- Coinbase
- Kraken
- Binance, where jurisdiction/product eligibility permits

### Why this pattern

Kaiko has strong documented depth, derivatives metrics, timestamps and multi-venue normalization. CoinAPI provides a second normalized path with REST/WebSocket/order-book coverage and transparent self-serve pricing.

Neither is treated as sufficient evidence of venue truth by itself.

For any traded venue, the direct venue feed remains a critical cross-check because:
- order-flow is venue-specific;
- exchange sequence and book semantics matter;
- aggregated vendor feeds may normalize or delay source-specific details.

### Conditions before P01-G

Still unresolved:
- Kaiko commercial quote and subscribed SLA;
- Kaiko algorithmic/non-display/raw-retention/model-use rights;
- CoinAPI non-display/raw-retention/redistribution terms;
- jurisdiction eligibility of target exchanges.

Result:

`CRYPTO_DATA = CONDITIONAL_SHORTLIST_ONLY`

## 6. Forex market data strategy

### Preferred architecture

**Primary class:** independent multi-source/multi-asset FX feed  
**Backup class:** separate FX quote/API vendor  
**Cross-check:** actual eligible execution-broker quote plus futures proxy where useful

Conditional candidates:

Primary:
- dxFeed

Backup:
- Massive
- Twelve Data

Broker quote references:
- OANDA
- IBKR
- Saxo

### Critical FX rule

No source may be called `GLOBAL_SPOT_FX_VOLUME`.

All volume/order-flow inputs remain explicitly labeled as:
- broker volume proxy;
- tick-volume proxy;
- ECN proxy;
- futures proxy;
- aggregated proxy.

Coverage confidence is mandatory.

### Why broker quote is a cross-check, not the sole market view

A broker quote is operationally important because it is the executable price for that broker/account, but it does not represent the entire OTC FX market.

The system therefore needs:
- an independent market-context feed;
- the broker's executable quote;
- optional centralized futures context.

Result:

`FOREX_DATA = CONDITIONAL_SHORTLIST_ONLY`

## 7. Futures / commodity context strategy

For Gold, WTI, Brent and futures-derived context:

**Conditional operational primary:** Databento  
**Conditional backup:** dxFeed  
**Authority:** CME / ICE / Cboe as applicable

The exchange or index owner remains authoritative for:
- contract specifications;
- trading calendar;
- benchmark definition;
- entitlement/licensing terms.

Databento is attractive for normalized live/historical/replay workflows, but exact exchange entitlements and required L2/L3/history tiers remain unresolved.

Result:

`FUTURES_CONTEXT = CONDITIONAL_SHORTLIST_ONLY`

## 8. Index context strategy

For SPX / NDX / VIX:

**Authority:** index owner / licensed source  
**Operational vendor:** to be selected only after rights resolution  
**Possible secondary vendors:** dxFeed, Massive, Databento where dataset coverage applies

Important:

A secondary vendor cannot replace index-owner licensing requirements.

P01-E already showed that display/non-display/index usage rights may require specific agreements.

Result:

`INDEX_CONTEXT = RIGHTS_BLOCKED_FOR_PRODUCTION_SELECTION`

## 9. Macro / rates strategy

This area is stronger and simpler.

### Preferred architecture

**Primary authority:** direct official source  
**Backup/normalization/revision layer:** FRED/ALFRED

Examples:
- Federal Reserve / FRED / ALFRED
- BLS
- BEA
- CFTC
- U.S. Treasury
- later ECB/Eurostat, BoE, BoJ, BIS, IMF, World Bank, EIA/OPEC/IEA

Official source controls:
- event/release identity;
- initial release;
- publication timestamp.

FRED/ALFRED is useful for:
- normalized retrieval;
- revisions;
- vintage history;
- cross-series research.

Result:

`MACRO_RATES = STRONG_BASELINE_CANDIDATE`

## 10. On-chain strategy

On-chain information is supplemental intelligence, not exchange market data.

### Preferred architecture

**Convenient indexed source:** Blockscout  
**Independent verification:** chain state / direct node / second indexer

Critical signals should be reproducible against an independent path before being treated as high-confidence.

Result:

`ONCHAIN = SUPPLEMENTAL_ONLY`

## 11. Execution redundancy — Crypto

Candidate pool:
- Coinbase Advanced
- Kraken
- Binance, where legally/product eligible

P01-F does not rank or select them.

Before any venue can become Primary or Backup it must pass:

- explicit Owner jurisdiction/product eligibility;
- account/API permission review;
- sandbox/testnet/controlled certification;
- client-order-ID and idempotency validation;
- order/fill/cancel/reject reconciliation;
- current fee/funding model;
- P15 Risk policy compatibility;
- P16 Pre-Trade Firewall compatibility;
- P20 execution certification.

### Failover rule

If the active venue becomes uncertain:

1. halt new orders;
2. determine whether any order acknowledgement/fill is uncertain;
3. reconcile broker/exchange state;
4. move system to `DEGRADED` / `SAFE_MODE` as required;
5. protect/reduce existing exposure at the current venue if possible;
6. only then authorize **new future intents** on a separately certified backup.

Never replay an uncertain live order blindly on the second venue.

## 12. Execution redundancy — Forex

Candidate pool:
- OANDA
- IBKR
- Saxo

Same principles apply.

A backup Forex broker must have:
- separate legal/account state;
- independent reconciliation;
- eligible API trading;
- validated paper/practice/SIM path;
- known financing/spread/commission behavior;
- independent position/balance tracking.

No broker outage automatically becomes a cross-broker market order.

## 13. Data failover policy

Automatic data failover is **not authorized in P01**.

It can only be enabled after:

- P05 provider adapters, heartbeat, gap recovery;
- P07 trusted-data/provenance controls;
- empirically defined divergence thresholds;
- continuously validated warm backup;
- failover and recovery tests;
- A2/A5/A9 authorization under the relevant Task Contract.

Future switch sequence:

1. detect primary degradation;
2. mark primary unhealthy;
3. validate backup freshness/schema/sequence state;
4. compare against an authoritative/cross-check source;
5. switch only the affected domain;
6. preserve provider provenance on every event;
7. keep primary under observation;
8. validate recovery before switching back.

## 14. Fail-closed conditions

Affected data/decision paths become unavailable when:

- Primary and Backup are both stale/unavailable;
- divergence exceeds an approved future threshold and cannot be adjudicated;
- entitlement/licence is invalid or expired;
- schema/sequence integrity fails;
- risk-relevant source provenance is missing.

A missing source must not silently become zero/neutral data.

## 15. Concentration controls

### Market data

- critical tradable data must not use one vendor as both operational source and independent validator;
- two aggregators using identical upstream sources are not automatically independent;
- direct venue/exchange/agency references remain important;
- provenance must survive normalization.

### Execution

- high-autonomy production eventually requires more than one eligible execution candidate;
- backup venues are independently certified;
- capital/counterparty concentration limits are formally owned by P15;
- withdrawal permission is not part of the trading API requirement.

## 16. Fresh evidence check — 2026-10-04

P01-F revalidated key Candidate documentation:

- Kaiko official docs continue to expose real-time order-book/top-of-book data, sequence/timestamps and derivatives metrics.
- CoinAPI currently documents REST/WebSocket with plan-specific trades, quotes and order-book access.
- dxFeed currently documents global Forex/crypto/futures/index delivery and multiple API modes.
- Databento continues to document live/historical delivery and pass-through market-data licensing treatment.
- OANDA v20 still documents account-specific pricing streams and notes that the stream does not emit every underlying price event.
- IBKR currently documents tiered Spot FX commissions and multi-dealer liquidity aggregation.

This check confirms candidate relevance; it does not resolve jurisdiction, licensing or final selection.

## 17. P01-G prerequisites

P01-G cannot issue a final production baseline until these are resolved:

1. Owner country/account jurisdiction;
2. individual vs entity account;
3. retail/professional/accredited/institutional status where applicable;
4. intended products and candidate venues;
5. Kaiko/dxFeed or other enterprise quotes if shortlisted;
6. non-display/algorithmic/storage/model-use rights;
7. index/exchange entitlements;
8. required SLA/support level;
9. fresh revalidation of candidate availability and terms.

## 18. Result

Primary/Backup architecture = `DESIGN_COMPLETE`  
Crypto provider selection = `PENDING_P01_G`  
Forex provider selection = `PENDING_P01_G`  
Context-data selection = `PENDING_P01_G / RIGHTS_REVIEW`  
Execution-venue selection = `PENDING_JURISDICTION_AND_P01_G`  
Automatic live broker failover = `FORBIDDEN`  
Live Trading = `DISABLED`  
Auto Trading = `DISABLED`

Machine-readable artifact:

`docs/03-research/p01-f-primary-backup-provider-strategy.json`

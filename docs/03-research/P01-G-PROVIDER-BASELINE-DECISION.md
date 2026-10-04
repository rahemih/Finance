# P01-G — Provider Baseline Decision

STATE = CANONICAL_COMPLETE  
TASK = `FIN-P01-WG-004`  
PHASE = `P01 — Market / Provider / Compliance Research`  
GATE = `G1_PROVIDER_BASELINE`  
COUNTRY_LOCATION_INPUT = `DO_NOT_USE / DO_NOT_ASSUME`  
FINAL_EXECUTION_VENUE = `DEFERRED`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Owner directive

P01-G is explicitly country-neutral.

No country, residence, IP-derived location, account-location metadata or inferred jurisdiction is used to rank market-data providers or execution candidates.

Known non-location inputs:
- account type: individual / personal;
- client classification: unknown;
- intended products: Forex, Crypto Spot, Crypto Futures/Perpetuals;
- budget preference: unknown;
- technical cost default for comparison only: BALANCED.

Actual legal entity, product eligibility, KYC/client classification and broker/exchange availability are revalidated only at the real account-opening / production-activation gate.

## 2. G1 interpretation

The canonical roadmap defines P01-G as an evidence-backed shortlist and rejection-reason decision, not account opening.

G1 therefore answers:

> Do we have a technically viable, legally-aware, cost-aware and resilient provider baseline that is sufficient to design a portable architecture in P02?

It does **not** answer:

> Which exact broker legal entity may a specific person open today?

That later question is intentionally deferred.

## 3. P01 hard gates

The country-neutral G1 hard gates are:

1. technical capability fit;
2. known data-rights constraints;
3. security / least-privilege compatibility;
4. primary/backup independence;
5. operations / recovery path;
6. cost envelope known or explicitly `QUOTE_REQUIRED`;
7. provider portability / no single-provider lock-in.

The following are **activation gates**, not P01 architecture gates:
- jurisdiction/product eligibility;
- retail/professional/accredited classification;
- final legal entity;
- KYC/account approval;
- final contract/data entitlement;
- live API permissions.

Unknown activation facts do not authorize trading, but they no longer block P02 architecture.

## 4. Country-neutral reference baseline

### Crypto market data

Primary reference:
- **Kaiko**

Backup reference:
- **CoinAPI**

Mandatory future cross-check:
- direct venue-native feed for every actually traded venue.

Evidence-derived technical reference scores:
- Kaiko: **80.5 / 100**
- CoinAPI: **78.5 / 100**

Activation blockers remain:
- commercial quote / SLA where applicable;
- non-display / algorithmic / raw-retention / model-use rights;
- actual traded-venue account/product eligibility.

### Forex market data

Primary reference:
- **dxFeed**

Backup reference:
- **Twelve Data**

Secondary validation:
- **Massive**

Forex-specific technical scores:
- dxFeed: **77.5 / 100**
- Twelve Data: **77.0 / 100**
- Massive: **72.0 / 100**

Mandatory rules:
- actual execution-broker quote becomes an additional live cross-check at activation;
- no source is labeled `GLOBAL_SPOT_FX_VOLUME`;
- broker/tick/ECN/futures/aggregated volume remains proxy-labeled with coverage confidence.

Activation blockers remain:
- commercial quote/SLA;
- exact contributor/coverage semantics;
- business non-display/automated-use rights;
- actual broker account/product eligibility.

### Futures / commodity / index context

Primary reference:
- **Databento**

Backup reference:
- **dxFeed**

Authority:
- CME / ICE / Cboe / index owner as applicable.

Databento technical reference score:
- **88.5 / 100**

Activation blockers:
- exchange/index entitlements;
- required depth/history tier;
- production SLA/support;
- source-specific non-display/derived-data rights.

### Macro / rates

Primary authority:
- **Direct official sources**

Secondary / revision-aware aggregator:
- **FRED / ALFRED**

FRED/ALFRED reference score:
- **92.0 / 100**

Important:
- source-agency releases remain authoritative;
- FRED availability does not override third-party series rights.

### On-chain

Supplemental reference:
- **Blockscout**

Independent verification:
- direct node or second indexer when a signal becomes risk-relevant.

Blockscout is not a replacement for exchange market data.

## 5. Execution architecture reference candidates

These are **architecture reference candidates**, not production account selections.

### Crypto

Reference order by technical evidence:
1. **Kraken — 84.5**
2. **Binance — 83.5**
3. **Coinbase Advanced — 76.5**

P02 may use these capabilities to design a portable crypto execution adapter contract.

Actual production venue:
`DEFERRED_TO_ACCOUNT_OPENING / PRODUCTION_ACTIVATION`

### Forex

Reference order by technical evidence:
1. **Saxo OpenAPI — 89.5**
2. **OANDA v20 — 86.5**
3. **Interactive Brokers — 85.0**

P02 may use these capabilities to design a portable Forex execution adapter contract.

Actual production broker:
`DEFERRED_TO_ACCOUNT_OPENING / PRODUCTION_ACTIVATION`

## 6. Scoring rules

Scores are deterministic evidence summaries only.

They do **not**:
- make a legal eligibility decision;
- grant API authority;
- authorize subscriptions;
- authorize account opening;
- authorize Live or Auto Trading.

A later candidate can be technically top-ranked and still be rejected at activation because of legal entity, client class, contract, permissions or product availability.

## 7. Explicit rejections / deferrals

Rejected:
- one provider for every data domain;
- treating two aggregators as independent without upstream-source analysis;
- broker quote as global FX market truth;
- blind live cross-broker order replay/failover;
- using country/location in P01-G ranking.

Deferred:
- final crypto execution venue;
- final Forex execution broker;
- final provider commercial contract;
- exchange/index entitlements;
- real client classification;
- any jurisdiction-specific product decision.

## 8. G1 result

P01-A through P01-F are canonical.

P01-G now has:
- a provider-neutral/country-neutral shortlist;
- known constraints;
- cost/rights unknowns explicitly labeled;
- plausible primary/backup/cross-check paths;
- execution reference candidates;
- no single-provider architecture assumption;
- no hidden use of location.

Therefore:

`G1_PROVIDER_BASELINE = PASS`

This PASS authorizes **P02 — Master Architecture** only.

It does **not** authorize:
- account opening;
- KYC;
- provider contracts;
- credentials;
- funding;
- Demo/Shadow/Live execution;
- automatic trading.

## 9. Safety state

Accounts = NONE  
KYC = NONE  
Subscriptions/contracts = NONE  
Credentials = NONE  
Funding = NONE  
Orders = NONE  
Demo Trading = NOT_STARTED  
Shadow Trading = NOT_STARTED  
Live Trading = DISABLED  
Auto Trading = DISABLED


## 10. Canonical closure

Task: `FIN-P01-WG-004 = CANONICAL_COMPLETE`  
Lock: RELEASED  
P01 phase: CANONICAL_COMPLETE  
G1_PROVIDER_BASELINE: PASS  
Next phase: `P02 — Master Architecture`

# G1 — Provider Baseline Dossier

GATE = `G1_PROVIDER_BASELINE`  
TASK = `FIN-P01-WG-004`  
STATE = `HUMAN_GATE`  
DATE = `2026-10-04`

## 1. Gate purpose

G1 determines whether Finance / NEXUS QUANT has a sufficiently evidenced market-data / execution-provider baseline to move from P01 research into P02 architecture.

G1 does not create accounts, credentials, subscriptions or trading authority.

## 2. Evidence already satisfied

- P01-A Market Universe = CANONICAL_COMPLETE
- P01-B Market Data Providers = CANONICAL_COMPLETE
- P01-C Broker / Exchange Inventory = CANONICAL_COMPLETE
- P01-D Jurisdiction & Compliance = CANONICAL_COMPLETE
- P01-E Cost / Licensing / Data Rights = CANONICAL_COMPLETE
- P01-F Primary / Backup Strategy = CANONICAL_COMPLETE
- source-of-truth / Governance / Toolchain controls = active
- Live Trading = DISABLED
- Auto Trading = DISABLED

## 3. Current conditional baseline

### Crypto market data
- Kaiko — conditional primary candidate
- CoinAPI — conditional secondary candidate
- venue-native feed — mandatory cross-check

### Forex market data
- dxFeed — conditional primary candidate
- Massive / Twelve Data — conditional backup candidates
- eligible broker quote — mandatory execution cross-check

### Futures / context
- Databento — conditional primary candidate
- dxFeed — conditional backup
- CME / ICE / Cboe / index owner — authority

### Macro / rates
- direct official source — primary authority
- FRED / ALFRED — secondary / revision-aware aggregation

### On-chain
- Blockscout — supplemental indexer
- chain state / second path — independent verification

### Crypto execution candidate pool
- Coinbase Advanced
- Kraken
- Binance

### Forex execution candidate pool
- OANDA
- Interactive Brokers
- Saxo

## 4. Blocking mandatory evidence

The following cannot be inferred:

- Owner/account jurisdiction
- individual vs entity account
- entity domicile if applicable
- client classification where material
- intended product set

The following commercial/rights items remain conditional where they affect the final shortlist:

- Kaiko / dxFeed enterprise quote and SLA if shortlisted
- non-display / algorithmic / storage / model-use rights
- exchange/index entitlements
- final eligible legal entity / broker product availability

## 5. Current gate result

`G1_PROVIDER_BASELINE = HUMAN_GATE`

Reason:

The project has enough technical/research evidence to prepare a conditional shortlist, but the execution/provider baseline cannot be legally or contractually finalized without explicit Owner jurisdiction/account facts.

## 6. Human Gate required

Minimum inputs:
1. account jurisdiction / country of residence;
2. individual vs company/entity;
3. client classification, or Unknown;
4. intended products;
5. optional cost preference.

No citizenship/tax-residency detail is requested unless later required by a specific shortlisted provider/regime.

## 7. Safety

Production provider selected: NO  
Production broker/exchange selected: NO  
Accounts/KYC: NONE  
Credentials: NONE  
Funding: NONE  
Orders: NONE  
Demo Trading: NOT_STARTED  
Shadow Trading: NOT_STARTED  
Live Trading: DISABLED  
Auto Trading: DISABLED

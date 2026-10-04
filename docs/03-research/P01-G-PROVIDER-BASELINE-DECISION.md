# P01-G — Provider Baseline Decision Preflight

STATE = HUMAN_GATE_PENDING  
TASK = `FIN-P01-WG-004`  
PHASE = `P01 — Market / Provider / Compliance Research`  
GATE = `G1_PROVIDER_BASELINE`  
FINAL_PROVIDER_SELECTION = `NOT_PERFORMED`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Objective

P01-G is the final main-roadmap workstream in P01.

Its purpose is to convert the research from P01-A through P01-F into a defensible provider baseline:

- market-data primary/backup paths;
- execution venue candidate baseline;
- authoritative macro/context sources;
- explicit rejected/deferred alternatives;
- residual risks;
- G1 gate decision.

The final production baseline cannot be selected from technical quality alone. Jurisdiction, client class, data rights and product eligibility are hard gates.

## 2. Evidence already complete

P01-G starts with canonical evidence from:

- P01-A — Market Universe & Instrument Taxonomy
- P01-B — Market Data Provider Inventory
- P01-C — Broker / Exchange Inventory
- P01-D — Jurisdiction & Compliance
- P01-E — Cost / Licensing / Data Rights
- P01-F — Primary / Backup Provider Strategy

Therefore P01-G is a decision and gate phase, not another broad discovery phase.

## 3. Hard gates

A candidate can only enter final scoring if all mandatory hard gates pass.

### H1 — Jurisdiction / product eligibility

The provider/broker legal entity and product must be legal/available for the actual account jurisdiction and client class.

Unknown = BLOCKED.

### H2 — Client class

Retail / professional / accredited / institutional status must be explicit where it changes product access, leverage, market-data fees or terms.

Unknown where material = BLOCKED.

### H3 — Data rights

For production data use, required rights must explicitly cover the intended use, which may include:

- internal display;
- non-display;
- automated analysis;
- algorithmic use;
- storage;
- raw retention;
- derived data / model training;
- exchange/index entitlement.

Unknown mandatory rights = BLOCKED.

### H4 — Technical capability

The provider must meet the data/execution capability required by the target role.

### H5 — Security / permissions

The account/API model must support least privilege. Trading APIs must not require withdrawal authority.

### H6 — Resilience

The chosen primary and backup design must provide meaningful independence rather than duplicate the same failure domain.

### H7 — Operations / recovery

The candidate must support a testable failure/recovery path appropriate to its role.

## 4. Deterministic soft scoring

Soft scores are calculated only for candidates that pass the hard gates.

### Market-data weights

| Criterion | Weight |
|---|---:|
| Coverage / market fit | 20 |
| Data quality / provenance / timestamps | 20 |
| Real-time / history / replay / depth | 15 |
| Licensing / rights clarity | 15 |
| Resilience / backup fit | 10 |
| Cost transparency / economics | 10 |
| Operations / SLA / support | 10 |
| **Total** | **100** |

### Execution weights

| Criterion | Weight |
|---|---:|
| API order lifecycle / reconciliation | 25 |
| Market / liquidity / product fit | 20 |
| Sandbox / test / certification | 15 |
| Security / permissions | 15 |
| Fees / spread / financing | 10 |
| Resilience / support | 10 |
| Integration complexity | 5 |
| **Total** | **100** |

A high score cannot override a failed hard gate.

## 5. Current conditional shortlist

### Crypto market data

Conditional institutional primary:
- Kaiko

Conditional secondary:
- CoinAPI

Mandatory independent cross-check:
- direct venue-native feed for the traded venue

Current blockers:
- enterprise quote/SLA where required;
- non-display/algorithmic/raw-retention/model-use rights;
- target venue jurisdiction eligibility.

### Forex market data

Conditional primary:
- dxFeed

Conditional backups:
- Massive
- Twelve Data

Mandatory execution cross-check:
- quote from the eventual eligible execution broker

Current blockers:
- dxFeed commercial quote/SLA;
- exact contributor/coverage semantics;
- business non-display/automated rights;
- actual account jurisdiction.

### Futures / commodity context

Conditional primary:
- Databento

Conditional backup:
- dxFeed

Authority:
- CME / ICE / Cboe as applicable

Current blockers:
- exchange/index entitlements;
- required depth/history tier;
- production SLA/support.

### Macro / rates

Primary authority:
- direct official source

Secondary/revision-aware aggregation:
- FRED / ALFRED

This is the strongest currently available baseline because it follows official-first policy.

### On-chain context

Supplemental:
- Blockscout

Independent validation:
- chain state / direct node / second indexer

Blockscout is not a replacement for exchange market data.

## 6. Current execution candidate pools

### Crypto

- Coinbase Advanced
- Kraken
- Binance

No ordering is performed before Owner jurisdiction and product eligibility are known.

### Forex

- OANDA
- Interactive Brokers
- Saxo

No ordering is performed before Owner jurisdiction and account/client class are known.

## 7. Decisions already rejected

The following are rejected by design:

- one provider for all data domains;
- treating two aggregators as independent without upstream-source review;
- broker quote as global Spot FX market truth;
- blind automatic live cross-broker failover;
- production use where required data rights are unknown;
- inferring Owner jurisdiction from ChatGPT/account/network/location metadata.

## 8. Human Gate

P01-G has now reached a **real Owner Human Gate**.

To continue the final provider-baseline decision, the following must be supplied explicitly:

1. **Account jurisdiction / country of residence**  
   The country under which the trading/data accounts will actually be opened and operated.

2. **Account type**  
   Individual or company/entity.  
   If company/entity: country of registration.

3. **Client classification**  
   Retail / Professional or Accredited / Institutional / Unknown.

4. **Intended products**  
   Choose all relevant:
   - Crypto Spot
   - Crypto Perpetual/Futures
   - Forex Spot / leveraged FX / CFD as applicable

5. **Optional budget preference**  
   - Low-cost
   - Balanced
   - Reliability-first
   - Unknown

Citizenship or tax residency will only be requested later if a shortlisted provider/regime specifically requires it. The project does not collect extra personal data without a concrete need.

## 9. What happens immediately after the Human Gate

A8 + A10:
- revalidate the supplied jurisdiction using official regulator sources and Legal Data Hunter.

A2 + A1:
- revalidate candidate provider availability, rights and technical fit.

A5:
- reject any candidate with unresolved counterparty/product/risk eligibility.

A9:
- validate operational redundancy and recovery fit.

A0:
- run the deterministic decision process and prepare the G1 dossier.

If mandatory evidence passes:

`G1_PROVIDER_BASELINE = PASS`

and:

`P01 = CANONICAL_COMPLETE`

Then the project may move to:

`P02 — Master Architecture`

No runtime trading implementation is authorized by G1 itself.

## 10. Current status

P01-A = COMPLETE  
P01-B = COMPLETE  
P01-C = COMPLETE  
P01-D = COMPLETE  
P01-E = COMPLETE  
P01-F = COMPLETE  
P01-G = `HUMAN_GATE_PENDING`

G1 = `HUMAN_GATE`

Accounts / KYC / credentials / subscriptions / funding / orders = `NONE`  
Live Trading = `DISABLED`  
Auto Trading = `DISABLED`

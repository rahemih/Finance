# P09-A — Volume Taxonomy / Proxy Labels

Task: `FIN-P09-WA-001`  
Linear: `HOS-225`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Lead: A2 Data  
Support: A0, A1, A3, A4, A6, A8, A9, A10

## Objective

Establish the canonical provider-neutral ontology for volume observations before any Delta/CVD, Volume Profile, order-book or liquidity model is allowed to consume them.

## Canonical rule

Spot FX does not expose one centralized, consolidated volume tape. NEXUS QUANT therefore must never label a broker, ECN, tick-count or related futures series as true total spot-FX market volume.

Every spot-FX volume observation must carry:

- an explicit proxy kind;
- provider and venue/feed identity;
- coverage scope;
- coverage confidence in integer basis points;
- explicit proxy target;
- event-time and as-of-time;
- trusted dataset version and quality-evidence digest.

## Governed volume kinds

| Kind | Meaning | Spot FX allowed |
|---|---|---:|
| `NATIVE_VENUE_VOLUME` | Native volume from one identified venue | No |
| `AGGREGATED_VENUE_VOLUME` | Aggregate across explicitly identified venues | No |
| `TICK_VOLUME_PROXY` | Tick/update count used as activity proxy | Yes |
| `BROKER_VOLUME_PROXY` | Broker-observed flow/volume proxy | Yes |
| `ECN_VOLUME_PROXY` | ECN-observed activity/volume proxy | Yes |
| `FUTURES_VOLUME_PROXY` | Related futures volume used as spot-FX proxy | Yes |

## Fail-closed conditions

- unknown market class or volume kind;
- negative volume;
- future event time relative to as-of time;
- invalid dataset/evidence hash;
- spot-FX native/aggregated volume label;
- spot-FX proxy with no explicit proxy target;
- spot-FX coverage scope claiming GLOBAL, CONSOLIDATED or TOTAL_MARKET;
- native/aggregated venue volume declaring a proxy target.

## Contract boundary

`VolumeObservation` is a data/provenance contract only. It contains no order side, size, leverage, stop, take-profit, broker execution or trade-decision field.

P09-B through P09-H remain separate governed workstreams.

## Validation

Local deterministic preflight before repository mutation:

- P09-A unit tests: 11/11 PASS;
- deterministic P09-A evidence twice: byte-identical PASS;
- no network or credentials required.

Canonical implementation and post-merge verification are complete. Closure reconciliation records the evidence below.

## Safety

- Production order-flow vendor: NOT_SELECTED
- Country assumption: NONE
- LIVE_TRADING: DISABLED
- AUTO_TRADING: DISABLED
- Direct trade/order authority: FORBIDDEN


## Canonical closure evidence

- Implementation PR: `#190` = MERGED
- Final implementation head: `250d52ef56a54fe16ed9c72b4f79b72af3f84ea0`
- Implementation merge SHA: `e1ef041ce84607cf6ef5c44d4a3588153efd8a5f`
- PR Governance: `38047638390` = SUCCESS
- PR artifact: `sha256:52fc0ae669baf05585abf890a5db7adc9ac2c1c8df5cf419a289a9a38321c8d6`
- Post-merge Governance: `38047708557` = SUCCESS
- Post-merge artifact: `sha256:d075fc65cc5afaf7a1d78ccb068e4a28e41f7f08ca103541fa1cc9341299cb76`
- Post-merge Branch Hygiene: `38047708566` = SUCCESS
- P09 tests: PASS
- deterministic P09-A evidence twice: PASS
- supply-chain / reproducibility controls: PASS

P09-B — Trades / Buy-Sell Flow / Delta / CVD becomes `READY_NOT_STARTED`.

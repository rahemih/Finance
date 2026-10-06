# NEXUS QUANT — P05-A Fresh Revalidation

STATE = CANONICAL_COMPLETE  
TASK = `FIN-P05-WA-001-R01`  
LINEAR = `HOS-190`  
DATE = 2026-10-06  
LEAD = A2 Data Agent

## Objective

Re-certify P05-A from the current canonical repository state instead of duplicating the already-merged Kaiko adapter.

The original P05-A implementation remains canonical unless this audit proves a defect.

## Fresh baseline

Canonical main at revalidation start:

`29264269488f414f9f333abe0eeaaa91f8516c21`

Original P05-A:
- task `FIN-P05-WA-001`;
- Linear `HOS-183` = Done;
- provider = Kaiko;
- first controlled identity = `cbse / spot / btc-usd`;
- production execution venue = NONE;
- provider credential = NONE;
- live connectivity = DISABLED_ENTITLEMENT_REQUIRED.

## Provider decision revalidation

P01-G remains authoritative:
- crypto primary reference = Kaiko;
- backup reference = CoinAPI;
- direct venue-native feed required later as the actual traded-venue cross-check.

No country/location is used in the provider ranking.

## Current official Kaiko revalidation

Fresh official documentation reviewed on 2026-10-06 confirms:
- Stream Market Update V1 remains available;
- Stream Orderbook L2 V1 remains available;
- Kaiko Stream examples use gRPC/Kaiko SDK;
- Market Update responses expose exchange/class/code/sequenceId and exchange/collection/event timestamps;
- HTTP APIs continue to use `X-Api-Key`.

Project policy remains conservative:
- HTTP gateway request specs are `HTTP_API_TESTING_ONLY`;
- no HTTP gateway is claimed as production stream transport;
- production transport remains `NOT_SELECTED`;
- canonical tests remain offline.

## Contract boundary

Provider-neutral:
- `packages/contracts/market_data.py`

Provider-specific:
- `adapters/market_data/kaiko.py`

The neutral package must not import Kaiko/provider implementation.

## Baseline re-test evidence

Latest canonical main Governance before R01:
- run `37426742704` = SUCCESS;
- P05 real-time data tests = `54/54 PASS`;
- P05-A deterministic evidence = `85cc09c51db715c7f2c55e46d84d0f55486fa48822bee8db2f964afcb71fb5e3`;
- strict Pyright = `0 errors / 0 warnings`;
- SBOM/license = PASS;
- Trivy HIGH/CRITICAL = PASS;
- reproducible clean-source build = PASS.

## Fresh edge tests

R01 adds explicit regression coverage for:
- RFC3339 timezone offsets;
- >9 fractional timestamp precision rejection;
- NaN/Infinity numeric rejection;
- invalid non-object HTTP `result` wrapper.

## Phase-boundary defect found

`scripts/ci/p04_exit.py` still printed:

`P05_STATE=NOT_STARTED_PENDING_OWNER_AUTHORIZATION`

after P05 had already become active.

This is a CI/state-reporting defect, not a market-data runtime defect.

Repair rule:
- P04 closure JSON keeps its historical handoff state;
- P04 exit regression verifies P04 remains canonical;
- the current phase is read from `CURRENT-STATE.md`;
- phase progression may advance beyond P04 without falsifying the historical closure record;
- CI prints the actual current phase instead of a stale historical P05 state.

## P05-D pause

HOS-188 is temporarily returned to Todo during this revalidation.

No P05-D mutation is performed by R01.

## Safety

Kaiko subscription = NONE  
Kaiko credential = NONE  
Provider network connection = DISABLED  
Orders/funding = NONE  
CANARY = DISABLED  
LIVE_TRADING = DISABLED  
AUTO_TRADING = DISABLED


## Closure evidence

Fresh implementation/revalidation:
- PR `#122` = MERGED;
- final head `200901c3f32b65155f0536a5664b59bf11d41109`;
- PR Governance `37430457151` = SUCCESS;
- PR artifact `11396348740`;
- PR artifact digest `sha256:b976f1f8dff026fbb177b151cc03f5bc01b953d44492a7cfb26d02eed7486192`;
- merge SHA `a72391a0889150f69080e9eb7e31b5d1d050b422`;
- post-merge Governance `37430728907` = SUCCESS;
- post-merge Branch Hygiene `37430728968` = SUCCESS;
- post-merge artifact `11396084336`;
- post-merge artifact digest `sha256:67faadef077183adea27d5e5e5cda6a35b28d78e2117bec8933faea49588cc09`.

Fresh certification:
- P05 tests: `58/58 PASS`;
- foundation tests: `22/22 PASS`;
- strict Pyright: `0 errors / 0 warnings`;
- `P05A_PROVIDER_BASELINE=PASS`;
- `P05A_PROVIDER_NEUTRAL_BOUNDARY=PASS`;
- `P05A_CONNECTIVITY_SAFETY=PASS`;
- `P05A_REVALIDATION=PASS`;
- deterministic P05-A evidence SHA-256 unchanged: `85cc09c51db715c7f2c55e46d84d0f55486fa48822bee8db2f964afcb71fb5e3`;
- SBOM/license/Trivy = PASS;
- reproducible build = PASS;
- post-merge artifact SHA-256 `43be33e5b321dc8c3aba4e390c107dfbb70c7a2f43d3c791a3dd485b3e7f644d`;
- rollback manifest SHA-256 `8fa4c32b6cf1b85a64fe61708e621ef130d901c8a40c82ed78c71bd1211581b2`.

Finding repaired:
- `PHASE-BOUNDARY-DRIFT-001` = REPAIRED;
- P04 historical handoff remains immutable evidence;
- CI now reports `CURRENT_PHASE=P05 — Real-Time Data / ACTIVE`.

Verdict:
- original Kaiko adapter defect found: NONE;
- fresh edge tests added: 4;
- original P05-A remains canonical;
- `FIN-P05-WA-001-R01 = CANONICAL_COMPLETE` after closure merge;
- P05-D remains Todo/paused.

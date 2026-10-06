# NEXUS QUANT — P05-A Crypto Real-Time Adapter / Kaiko Baseline

STATE = P05-A CANONICAL_COMPLETE  
TASK = `FIN-P05-WA-001`  
LINEAR = `HOS-183`  
DATE = 2026-10-05  
LEAD = A2 Data Agent

## 1. Objective

P05-A introduces the first production-zone market-data code in NEXUS QUANT.

The implementation remains provider-portable:
- provider-neutral envelope/types live under `packages/contracts`;
- Kaiko-specific translation lives under `adapters/market_data`;
- no strategy, risk, execution or UX code imports the provider implementation.

First controlled feed identity:

`Kaiko / cbse / spot / btc-usd`

This is a **market-data integration reference only**. It does not select Coinbase or any other venue for trade execution.

## 2. Fresh provider evidence

The P01-G canonical baseline selected:
- Crypto market-data primary reference: **Kaiko**;
- backup reference: **CoinAPI**;
- direct venue-native feed required later as a traded-venue cross-check.

Official Kaiko documentation was revalidated on 2026-10-05.

Current documented Stream behavior relevant to P05-A:
- Level 1 tick trades are available through Stream;
- Level 2 tick-level all bids/asks are available through Stream;
- L2 starts with a full snapshot then continuous updates;
- a later full snapshot must replace the local snapshot;
- amount `0` means downstream book state should remove that price level;
- `sequenceId` is lexicographically sortable;
- messages expose `tsExchange`, `tsCollection`, and `tsEvent`;
- testing HTTP examples use `X-Api-Key`.

Official source pages:
- https://docs.kaiko.com/explore-our-data/subscriptions-channel-availability
- https://docs.kaiko.com/stream/cefi-spot-market-data/all-trades.md
- https://docs.kaiko.com/stream/cefi-spot-market-data/bids-and-asks.md
- https://www.kaiko.com/about-kaiko/pricing-and-contracts

Kaiko pricing/subscription remains commercial/custom. P05-A does not claim an entitlement.

## 3. Contract boundary

Provider-neutral contract owns:
- provider identifier;
- provider-native instrument identity;
- event kind;
- provider sequence ID;
- exchange timestamp;
- collection timestamp;
- provider-event timestamp;
- local receive timestamp;
- typed trade/order-book payload;
- immutable provider metadata.

P05-A intentionally does **not** finalize:
- canonical cross-provider symbol IDs;
- universal clock/freshness policy;
- canonical gap metadata;
- cross-provider normalization.

Those belong to P05-D/P05-F.

## 4. Timestamp policy

Kaiko timestamps can carry nanosecond precision.

P05-A stores:
- original RFC3339 text;
- exact integer epoch nanoseconds.

The parser does not down-cast provider timestamps to floating-point seconds.

The caller supplies `received_at_ns`, which makes parsing deterministic in tests and keeps receive-time measurement under the ingestion runtime rather than hidden inside the parser.

## 5. Sequence policy

Kaiko documents `sequenceId` as lexicographically sortable.

P05-A therefore supports:
- FIRST;
- ADVANCING;
- DUPLICATE;
- OUT_OF_ORDER.

It does **not** claim IDs are contiguous. Missing-data/gap recovery is P05-F scope.

## 6. Order-book semantics

Supported provider update types:
- `SNAPSHOT`;
- `UPDATE`;
- `UPDATED` accepted as a documented/observed naming alias and normalized to `UPDATE`.

The parser preserves zero-amount levels. It does not silently delete them because local-book mutation belongs to downstream book-state logic.

A new snapshot is preserved as `SNAPSHOT`; downstream state must replace its existing book.

## 7. Credential handling

P05-A configuration accepts only a secret handle such as:

`secret://market-data/kaiko/api-key`

No raw API key is stored in config, source, fixture or test.

Request specifications expose:
- the Kaiko **HTTP API testing endpoint** only;
- HTTP method;
- required API-key header name;
- secret handle;
- deterministic request JSON;
- explicit `HTTP_API_TESTING_ONLY` intended-use marker.

Current official HTTP testing request shapes are preserved exactly:

Trade:
```json
{
  "instrumentCriteria": {
    "exchange": "cbse",
    "instrumentClass": "spot",
    "code": "btc-usd"
  },
  "commodities": ["SMUC_TRADE"]
}
```

Level 2:
```json
{
  "instrumentCriteria": {
    "exchange": "cbse",
    "instrumentClass": "spot",
    "code": "btc-usd"
  }
}
```

They do not resolve the secret. The HTTP/cURL path is not declared production transport; Kaiko documents this API path as testing-oriented. Production stream transport selection remains a later governed connectivity concern.

## 8. Live connectivity

Canonical P05-A state:

`LIVE_PROVIDER_CONNECTIVITY = DISABLED_ENTITLEMENT_REQUIRED`

Reason:
- no Kaiko subscription/trial is claimed;
- no API key exists in repository state;
- no licensing/entitlement is assumed.

Canonical CI is entirely offline.

A later governed activation task may resolve the secret handle and open a provider stream only after contract/entitlement review.

## 9. Real type checking

P05-A is the first product-source task.

Required CI therefore activates:
- `jakebailey/pyright-action` v3.0.2;
- action commit `8ec14b5cfe41f26e5f41686a31eb6012758217ef`;
- Pyright `1.1.414`;
- strict `pyrightconfig.json`;
- Python target `3.14`.

Action license was revalidated as MIT.

The prior P04 `PASS_NO_PRODUCT_SOURCE` readiness state becomes a real enforced typecheck.

## 10. Deterministic certification

Canonical tests are offline and cover:
- current Kaiko HTTP testing request contract;
- direct provider payload and HTTP `result` wrapper equivalence;
- valid trade mapping;
- valid snapshot/update mapping;
- nanosecond timestamp preservation;
- zero-amount book semantics;
- duplicate/out-of-order sequence behavior;
- invalid instrument;
- invalid timestamp;
- invalid levels;
- raw-secret and empty-secret-handle rejection;
- request-spec secret isolation;
- deterministic repeated parsing.

A deterministic evidence generator serializes representative adapter outputs twice and CI requires byte equality.

## 11. Safety

Production subscription: NONE  
Provider API credential: NONE  
Provider network connection: DISABLED  
Execution venue selection: NONE  
Orders/funding: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Handoff

After canonical closure:

`P05-B — Forex Real-Time Adapters`

P05-A does not start P05-B itself.


## 13. Canonical closure evidence

Implementation:
- PR `#115` = MERGED;
- final head `9254ee3f6702ebee2abf7c06e9f05598d75b5bb7`;
- PR Governance `37295694293` = SUCCESS;
- PR artifact `11337813810`;
- PR artifact digest `sha256:da7cbba2f5c06ac50fc52f6e2140bf4de30cba1e92b21b04677edc55cccc21b5`;
- implementation merge SHA `163de8942e2b3382c7df8d416263a599e92eb1e6`;
- post-merge Governance `37295876778` = SUCCESS;
- post-merge Branch Hygiene `37295876816` = SUCCESS;
- post-merge artifact `11338213207`;
- post-merge artifact digest `sha256:646b44af473c54b38f8c765324742376d5fc4e34bc00f7cba8708a525c6ad799`.

Certification:
- strict Pyright 1.1.414 = `0 errors / 0 warnings`;
- P05-A adapter tests = `17/17 PASS`;
- deterministic adapter evidence SHA-256 = `85cc09c51db715c7f2c55e46d84d0f55486fa48822bee8db2f964afcb71fb5e3`;
- CycloneDX/license policy = PASS;
- Trivy HIGH/CRITICAL gate = PASS;
- reproducible build = PASS;
- reproducible artifact SHA-256 = `f6df8a2099ea9aaf7d332d4eebf6c64a86b6e8e429a11f882bb1071f5c4c8ade`;
- post-merge rollback manifest SHA-256 = `0adf25329fc86f4afe22ec0d653685d376869c15dc2cdd187188f41f935aaeb0`.

Code-review repairs before merge:
- Kaiko HTTP testing request contract aligned to current official `instrumentCriteria` shapes;
- trade test request includes `SMUC_TRADE`;
- direct payload + HTTP `result` wrapper both supported;
- HTTP request specs explicitly marked `HTTP_API_TESTING_ONLY`;
- empty/raw credential handles rejected;
- invalid receive timestamp types fail closed with adapter-domain error;
- production transport remains `NOT_SELECTED`.

Closure:
- `FIN-P05-WA-001 = CANONICAL_COMPLETE`;
- `LOCK-FIN-P05-WA-001-01 = RELEASED`;
- P05 remains ACTIVE;
- next workstream: `P05-B — Forex Real-Time Adapters`.


## 14. Fresh revalidation R01

Owner requested P05-A to be revalidated from scratch on 2026-10-06.

R01 does not duplicate the already-canonical adapter. It independently revalidates:
- current official Kaiko Stream/OpenAPI references;
- provider-neutral boundary;
- credential/network safety;
- strict Pyright;
- deterministic evidence;
- edge-case parser behavior.

R01 also repairs a cross-phase CI drift where the persistent P04 exit guard was still printing the historical P05 handoff state as if it were the current P05 state.

Linear: `HOS-190`  
Task: `FIN-P05-WA-001-R01`  
State: CANONICAL_COMPLETE / PENDING CLOSURE MERGE


Fresh revalidation implementation evidence:
- R01 PR `#122` = MERGED;
- merge SHA `a72391a0889150f69080e9eb7e31b5d1d050b422`;
- PR Governance `37430457151` = SUCCESS;
- post-merge Governance `37430728907` = SUCCESS;
- post-merge Branch Hygiene `37430728968` = SUCCESS;
- P05 tests `58/58 PASS`;
- foundation tests `22/22 PASS`;
- strict Pyright `0 errors / 0 warnings`;
- persistent P05-A boundary guard = PASS;
- original deterministic evidence digest unchanged;
- phase-boundary CI drift = REPAIRED;
- original P05-A adapter = NO DEFECT FOUND.

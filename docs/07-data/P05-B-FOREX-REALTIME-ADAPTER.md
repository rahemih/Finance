# NEXUS QUANT — P05-B Forex Real-Time Adapter / dxFeed Quote Baseline

STATE = P05-B CANONICAL_COMPLETE  
TASK = `FIN-P05-WB-001`  
LINEAR = `HOS-184`  
DATE = 2026-10-05  
LEAD = A2 Data Agent

## 1. Objective

P05-B establishes the first Forex real-time market-data adapter baseline.

First controlled identity:

`FX:EUR/USD:SPOT_OTC`

Provider reference:

`dxFeed / Quote / EUR/USD`

This is market-data ingestion only. It does not select an execution broker or venue.

## 2. Why Quote, not Trade

Forex is decentralized OTC.

The canonical P01 universe already forbids representing a single broker/vendor/tick source as consolidated global Spot FX volume.

Current dxFeed documentation also states that FX does not generally publish Trade/TimeAndSale events and that Quote is the bid/ask market event for FX.

Therefore P05-B consumes **Quote** semantics:
- bid price;
- ask price;
- bid-side change time;
- ask-side change time;
- quote-side source/exchange code where present;
- provider quote size where present.

No field is mapped to `GLOBAL_SPOT_FX_VOLUME`.

## 3. Transport direction

dxFeed's current modern integration direction is dxLink.WebSocket.

P05-B records that transport direction but does not open a live connection.

Canonical CI:
- network required = false;
- production endpoint = NOT_SELECTED;
- production entitlement/token = NOT_PROVISIONED;
- fixture/parser certification = offline.

REST/demos may be used only as documentation/testing references; they are not selected as production transport by P05-B.

## 4. Instrument identity

Provider symbol:

`EUR/USD`

Canonical identity:

`FX:EUR/USD:SPOT_OTC`

Provider envelope source scope:

`COMPOSITE_OTC`

This is a source-scope label, not an execution exchange or broker selection.

## 5. Quote contract

The provider-neutral Quote payload preserves:
- `bid_time`;
- `ask_time`;
- `bid_exchange_code`;
- `ask_exchange_code`;
- `bid_price`;
- `ask_price`;
- `bid_size`;
- `ask_size`;
- `time_nano_part`;
- explicit size semantics.

Size semantics:

`PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME`

## 6. Time semantics

dxFeed Quote exposes independent `bidTime` and `askTime`.

P05-B converts source milliseconds to nanoseconds exactly by multiplication and does not fabricate sub-millisecond precision.

`timeNanoPart` is preserved separately. It is not silently applied to both bid and ask times because that would invent side-specific precision not established by the source event.

`eventTime = 0` is represented as unavailable (`None`) rather than as Unix epoch.

Final cross-provider clock normalization is deferred to P05-D.

## 7. Size / liquidity semantics

Source `NaN` or absent quote size becomes `None`.

Finite non-negative size is preserved as provider quote size.

It must never be relabeled as:
- consolidated FX volume;
- global spot FX volume;
- exchange-wide executed volume.

Downstream volume/order-flow features must continue to use the proxy/source labels defined in P01-A.

## 8. Subscription descriptor

P05-B exposes only an offline descriptor:
- transport = `DXLINK_WEBSOCKET_REFERENCE`;
- event type = `Quote`;
- symbol = `EUR/USD`;
- endpoint = NONE;
- credential = NONE by default;
- intended use = `OFFLINE_CONTRACT_ONLY`.

If a credential reference is provided, only a non-empty `secret://` handle is accepted. The adapter never resolves the secret.

## 9. Offline certification

Canonical tests cover:
- Quote mapping;
- EUR/USD identity;
- independent bid/ask timestamps;
- no synthetic timestamp precision;
- zero/nonzero provider event time semantics;
- NaN/missing quote sizes;
- finite quote sizes;
- negative size rejection;
- invalid/non-finite price rejection;
- wrong symbol rejection;
- direct Quote object and REST testing-wrapper equivalence;
- raw/empty credential rejection;
- offline subscription descriptor;
- invalid receive timestamp rejection;
- deterministic parsing.

P05-B evidence is generated twice and byte-compared.

## 10. Boundary with later P05 work

Deferred:
- final provider-neutral canonical symbol master → P05-D;
- full clock model → P05-D;
- actual streaming runtime/backpressure → P05-E;
- reconnect/gap/failover → P05-F;
- latency/throughput/soak → P05-G;
- G4_REALTIME_DATA → P05-H.

## 11. Safety

dxFeed subscription/entitlement: NOT_PROVISIONED  
Production endpoint: NOT_SELECTED  
Production credential: NONE  
Broker execution integration: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Next

After canonical P05-B closure:

`P05-C — Context Market Ingestion`


## 13. Canonical closure evidence

Implementation:
- PR `#117` = MERGED;
- final head `e7c753669426bb586c468f6da53d9299503517dc`;
- PR Governance `37423688758` = SUCCESS;
- PR artifact `11393094970`;
- PR artifact digest `sha256:2d8d467e5c6c8f7838a53f368a9ea663a7a6c37088c2859536b2ba31d4bfe6b9`;
- implementation merge SHA `27f895fea7ffb5872c036995baf82325b86299b9`;
- post-merge Governance `37423795685` = SUCCESS;
- post-merge Branch Hygiene `37423795667` = SUCCESS;
- post-merge artifact `11393848905`;
- post-merge artifact digest `sha256:f5136687700fceb4bc6a19d85f53530d7ecf4575178809050d7f02a9d3533945`.

Certification:
- strict Pyright = `0 errors / 0 warnings`;
- P05 real-time data tests = `32/32 PASS`;
- P05-B deterministic evidence generated twice = PASS;
- CycloneDX/license policy = PASS;
- Trivy HIGH/CRITICAL gate = PASS;
- reproducible build = PASS;
- reproducible artifact SHA-256 = `45281fa66821554f9cd251ae2becbb90f5fe707382887d0a7195f4fb1907ce33`;
- post-merge rollback manifest SHA-256 = `289901235e42db3676ff396ceb88cb9882305af996c77117ac1b19e5d37f73c6`.

Closure:
- `FIN-P05-WB-001 = CANONICAL_COMPLETE`;
- `LOCK-FIN-P05-WB-001-01 = RELEASED`;
- P05 remains ACTIVE;
- next workstream = `P05-C — Context Market Ingestion`.

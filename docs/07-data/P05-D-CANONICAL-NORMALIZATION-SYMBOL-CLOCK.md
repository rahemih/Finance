# NEXUS QUANT — P05-D Canonical Normalization / Symbol Master / Clock Model

STATE = P05-D IMPLEMENTATION  
TASK = `FIN-P05-WD-001`  
LINEAR = `HOS-188`

## 1. Objective

P05-D creates the first provider-neutral normalization layer across the three closed P05 feeds:

- Kaiko BTC/USD Spot;
- dxFeed EUR/USD Spot OTC Quote;
- Databento GC Gold futures context.

The layer does not open network connections and does not grant trading authority.

## 2. Canonical identities

The Symbol Master baseline contains:

- `CRYPTO:BTC/USD:SPOT`;
- `FX:EUR/USD:SPOT_OTC`;
- `COMMODITY:GOLD:GC:FUTURES:COMEX`.

Provider symbols never become project-wide primary keys.

## 3. Alias resolution

### Kaiko

Exact alias:

`kaiko / cbse / spot / btc-usd`

→ `CRYPTO:BTC/USD:SPOT`

### dxFeed

Exact alias:

`dxfeed / COMPOSITE_OTC / forex_spot_otc / EUR/USD`

The provider envelope already carries `canonical_id`; P05-D requires that metadata claim to match the exact provider alias.

### Databento

The GC context uses a dynamic mapped child contract.

The canonical identity comes from governed metadata:

`COMMODITY:GOLD:GC:FUTURES:COMEX`

Required:
- subscription symbol = `GC.v.0`;
- mapped symbol metadata must equal `envelope.instrument.code`;
- mapped symbol remains a concrete provider contract identity and is never replaced by the continuous symbol.

P05-D therefore does not claim a static `GC.v.0 → child` mapping and does not implement automatic roll lifecycle.

## 4. Canonical event

`CanonicalMarketEvent` preserves:

- canonical ID;
- asset class;
- instrument role;
- event kind;
- provider;
- provider exchange;
- provider instrument class;
- provider symbol;
- sequence ID;
- source-envelope type;
- canonical clock;
- existing provider-neutral payload;
- deterministic provenance metadata.

The normalized payload is not reinterpreted into a new market meaning.

## 5. Clock model

Precision policy:

`SOURCE_PRESERVED_NO_SYNTHETIC_PRECISION`

### Kaiko

Preserved separately:
- exchange time;
- collection time;
- provider event time;
- local receive time.

Canonical event time uses `ts_event`.

### dxFeed

Preserved:
- optional provider event time;
- bid source time;
- ask source time;
- local receive time.

If provider event time is unavailable, canonical event time remains unavailable.

P05-D does **not**:
- substitute bid time;
- substitute ask time;
- merge bid/ask times;
- apply `timeNanoPart` to both sides;
- substitute local receive time.

### Databento

Preserved separately:
- optional provider event time;
- provider receive time (`ts_recv`);
- local receive time.

If `ts_event` is undefined, it remains unavailable. `ts_recv` is not promoted to event time.

## 6. Signed deltas

When source timestamps exist:

`event_to_local_delta_ns = local_receive_ns - provider_event_time_ns`

and:

`provider_receive_to_local_delta_ns = local_receive_ns - provider_receive_time_ns`

These are signed observations.

A negative value is preserved. P05-D does not silently clamp, correct or reinterpret it as pure network latency. Clock-drift alerting/operational thresholds are downstream P05 controls.

## 7. Fail-closed rules

Normalization rejects:
- unknown canonical ID;
- unknown provider alias;
- provider/canonical metadata mismatch;
- duplicate provider alias configuration;
- Databento mapped-symbol mismatch;
- duplicate metadata keys;
- empty sequence ID;
- invalid local receive timestamp.

## 8. Determinism

Canonical CI remains offline.

P05-D evidence normalizes the existing source-controlled fixtures for:
- Kaiko BTC trade;
- dxFeed EUR/USD quote;
- Databento GC MBP-1.

Evidence is generated twice and must be byte-identical.

## 9. Architecture boundary

`packages/market_data` is provider-neutral.

It imports:
- project-owned contracts;
- Python standard library.

It does not import `adapters.*`.

Provider-specific parsing remains under `adapters/market_data`.

## 10. Governance reconciliation

P05-D also corrects two status-reporting drifts:
- `EXECUTION-ROADMAP.md` current execution position is advanced to live P05;
- P04 exit output labels its old P05 boundary as `P04_CLOSURE_NEXT_PHASE_STATE`, not live `P05_STATE`.

The historical P04 closure snapshot itself is not rewritten.

## 11. Safety

Network connection: NONE  
Provider credentials resolved: NONE  
Trading authority: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Next

After canonical closure:

`P05-E — Streaming / Heartbeat / Backpressure`

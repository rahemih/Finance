# NEXUS QUANT — P05-C Context Market Adapter / Databento Gold MBP-1 Baseline

STATE = P05-C IMPLEMENTATION  
TASK = `FIN-P05-WC-001`  
LINEAR = `HOS-185`  
DATE = 2026-10-06  
LEAD = A2 Data Agent

## 1. Objective

P05-C establishes the first context-market real-time adapter baseline.

First controlled context identity:

`COMMODITY:GOLD:GC:FUTURES:COMEX`

Provider reference:
- Databento
- dataset: `GLBX.MDP3`
- schema: `mbp-1`
- continuous subscription symbol: `GC.v.0`

This feed is `CONTEXT_ONLY`. It does not authorize trading or select an execution venue.

## 2. Provider evidence

Current Databento documentation confirms:
- GC is available in the CME/Globex `GLBX.MDP3` dataset;
- MBP-1 provides event/receive timestamps, publisher/instrument IDs, venue sequence, event action/side, and top-of-book price/size/count fields;
- timestamps are integer nanoseconds since Unix epoch;
- DBN prices use fixed precision with scale `1e-9`;
- continuous symbology maps a continuous identifier to actual contracts and is not back-adjusted;
- an existing live continuous subscription does not silently remap itself after leader changes.

P05-C therefore preserves the requested continuous symbol and the mapped concrete contract as separate identities.

## 3. Undefined sentinels

Databento reserved undefined values are never interpreted as market data.

- `UNDEF_PRICE = INT64_MAX` → unavailable / `None`;
- `UNDEF_TIMESTAMP = UINT64_MAX` → unavailable / `None`.

Normal event/receive timestamps for the canonical fixture are required to be defined.

## 4. Price / quantity semantics

Defined integer prices are converted exactly:

`Decimal(raw_price) / 1_000_000_000`

No floating-point conversion is used.

GC is a centralized futures context feed. Sizes/counts are labeled:

`CENTRALIZED_FUTURES_VENUE_QUANTITY`

This does not imply Spot Gold OTC volume.

## 5. Provenance

The provider-neutral envelope preserves:
- provider;
- dataset;
- canonical context identity;
- subscription symbol;
- mapped contract symbol;
- publisher ID;
- provider instrument ID;
- venue sequence;
- provider event timestamp;
- Databento receive timestamp;
- local receive timestamp;
- action/side/depth;
- flags;
- `ts_in_delta`;
- BBO price/size/order counts.

## 6. Continuous mapping

`GC.v.0` means the volume-ranked continuous GC contract reference.

P05-C does not implement roll lifecycle. The concrete mapped contract must be supplied explicitly from symbology mapping evidence.

Automatic remap/resubscribe/roll behavior is deferred to P05-D/E/F.

## 7. Credential / transport

Canonical P05-C CI is offline.

Subscription descriptor records:
- dataset `GLBX.MDP3`;
- schema `mbp-1`;
- stype `continuous`;
- symbol `GC.v.0`;
- transport direction `DATABENTO_LIVE_REFERENCE`;
- endpoint = NOT_SELECTED;
- optional credential = non-empty `secret://` handle only.

The adapter never resolves the secret.

## 8. Safety

Databento entitlement: NOT_PROVISIONED  
Production endpoint: NOT_SELECTED  
Production credential: NONE  
Trading authorization: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 9. Next

After canonical closure:

`P05-D — Canonical Normalization / Symbol Master / Clock Model`

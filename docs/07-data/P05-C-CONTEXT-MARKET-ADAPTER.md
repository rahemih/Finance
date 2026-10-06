# NEXUS QUANT — P05-C Context Market Adapter / Databento Gold MBP-1 Baseline

STATE = P05-C CANONICAL_BASELINE  
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

## 5. MBP-1 record boundary

The baseline parser requires:
- `rtype = 1` for MBP-1;
- `depth = 0` for the one-level top-of-book record.

A lookalike payload from another Databento schema is rejected rather than silently coerced.

The fixture mapped child symbol `GCZ6` is deterministic test data only. It is not asserted to be the current live child mapping of `GC.v.0`; production mapping must come from provider symbology evidence.

## 6. Provenance

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

## 7. Continuous mapping

`GC.v.0` means the volume-ranked continuous GC contract reference.

P05-C does not implement roll lifecycle. The concrete mapped contract must be supplied explicitly from symbology mapping evidence.

Automatic remap/resubscribe/roll behavior is deferred to P05-D/E/F.

## 8. Credential / transport

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

## 9. Safety

Databento entitlement: NOT_PROVISIONED  
Production endpoint: NOT_SELECTED  
Production credential: NONE  
Trading authorization: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 10. Next

After canonical closure:

`P05-D — Canonical Normalization / Symbol Master / Clock Model`


## 11. Canonical closure evidence

Implementation:
- PR `#119` = MERGED;
- final implementation head: `9105f9fc6b9524d538b33aae45cb30d0a11f65f5`;
- implementation merge SHA: `ca835d18ba1628d9ffc5f1ba6e70d356b3181fa8`;
- PR Governance: `37425988146` = SUCCESS;
- PR artifact: `11395396532`;
- PR artifact digest: `sha256:896d4ef9b3a61d24ade39499eafb931aaa0cd0f6519ff1e6ad3a7c84fcc70939`;
- post-merge Governance: `37426163187` = SUCCESS;
- post-merge Branch Hygiene: `37426163231` = SUCCESS;
- post-merge artifact: `11395128218`;
- post-merge artifact digest: `sha256:8ef849bfcacc5f7630a63e5bd5ac29e948d961aa7c343e1aee1f763871d816cf`.

Validation:
- P05 tests: `54/54 PASS`;
- strict Pyright: `0 errors / 0 warnings`;
- deterministic P05-C evidence SHA-256: `ba1072b53db0abb3f36caff02962bb3bfdd95ac35bd87f11ae6c9f022df405c8`;
- SBOM/license/Trivy: PASS;
- reproducible artifact SHA-256: `cc59078d27cdb1a0198607366b987213bb66a7d38115002b8434526e6af0eb2a`;
- rollback manifest SHA-256: `a8c03077677eea74f076160da8947facad18e3777e565bfbad1dcf4a92602e1b`;
- reproducible file count: `325`.

Closure:
- `FIN-P05-WC-001 = CANONICAL_COMPLETE`;
- `LOCK-FIN-P05-WC-001-01 = RELEASED`;
- P05-D = `NOT_STARTED / READY`.

Safety unchanged:
- Databento production entitlement/API key = NOT_PROVISIONED;
- provider live network = DISABLED;
- trading authority = NONE;
- CANARY = DISABLED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

# P07-A — Schema Validators

Task: `FIN-P07-WA-001`  
Linear: `HOS-203`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Create the first P07 trusted-data control: deterministic fail-closed schema validation at canonical data boundaries.

## Validated contracts

P07-A validates four already-governed contracts:

1. `CanonicalMarketEvent` from P05;
2. `TimeSeriesRecord` from P06-C;
3. `FeatureMaterialization` from P06-F;
4. `ReplaySnapshot` from P06-G.

## Fail-closed behavior

Any critical schema violation returns `INVALID_CRITICAL`. The report contains stable issue codes and a deterministic fingerprint.

P07-A does not attempt to infer whether data is missing, duplicated, stale, statistically anomalous or divergent across providers. Those controls belong to P07-B through P07-D.

## Market-event schema checks

- required canonical/provider/instrument/sequence identifiers;
- non-negative local receive timestamp;
- event-kind/payload-type compatibility;
- canonical provenance consistency.

## Historical record checks

- supported canonical schema version;
- supported event kind;
- valid source SHA-256;
- safe relative raw archive reference;
- canonical payload is valid JSON and, by current policy, a JSON object.

## Feature/replay checks

Feature materializations and replay snapshots are validated through their canonical serialization and content-identity round trip. A content-address mismatch fails critical.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
Country assumption: NONE.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

P07-B remains blocked until P07-A canonical closure.

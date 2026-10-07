# P07-A — Schema Validators

Task: `FIN-P07-WA-001`  
Linear: `HOS-203`  
State: CANONICAL_COMPLETE  
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

P07-A implementation verification is complete. This closure reconciles the canonical state and makes P07-B READY_NOT_STARTED.

## Implementation evidence

- Implementation PR: `#151` = MERGED
- Final implementation head: `6e44a5aa11465b6814e57a0dd539a931632bec1b`
- Implementation merge SHA: `54f157ad002e85ea76c52a781ffa5697e4113883`
- PR Governance: `37669250431` = SUCCESS
- PR artifact: `sha256:2d447c5028e85320cbbf423cfcc38b797606f68a323a56af86947c3d06cb8464`
- Post-merge Governance: `37669545839` = SUCCESS
- Post-merge artifact: `sha256:38c19a7e82cff3bcfc1762f57c4ae694f9135e3bb8076fb881a04fdc3ef1aca2`
- Post-merge Branch Hygiene: `37669545843` = SUCCESS
- Lock: RELEASED

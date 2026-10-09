# P07-B — Completeness & Duplicate Checks

Task: `FIN-P07-WB-001`  
Linear: `HOS-204`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0, A1, A4, A8, A9, A10

## Objective

Add deterministic completeness and duplicate controls after P07-A schema validation.

## Explicit completeness contract

P07-B does **not** infer missing data from provider sequence gaps. Completeness is evaluated only against an explicit list of expected record IDs supplied by the governed caller. This prevents P07-B from stealing sequence semantics that belong to P07-C.

The batch must carry a SHA-256 reference to P07-A schema-validation evidence.

## Duplicate classes

Two key spaces are checked:

- **RECORD_ID:** repeated record identity;
- **LOGICAL_EVENT:** same canonical ID + provider + event time + sequence ID with distinct record IDs.

Each duplicate is classified:

- `EXACT_DUPLICATE`: repeated equivalent content;
- `CONFLICTING_DUPLICATE`: same identity/logical event with divergent content.

Both are critical because either may double-count or create ambiguous canonical truth.

## Completeness output

The report deterministically records:

- missing expected IDs;
- unexpected observed IDs;
- duplicate findings;
- schema-validation evidence digest;
- stable report fingerprint.

Unexpected IDs are reported but are not themselves treated as missing-data failure. Missing expected IDs and duplicates fail closed.

## Boundaries

Staleness, outlier and sequence-gap checks remain P07-C. Cross-provider divergence remains P07-D. Quarantine routing remains P07-F.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-C remains blocked until P07-B canonical closure.

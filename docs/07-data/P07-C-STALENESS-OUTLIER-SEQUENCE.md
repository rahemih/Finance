# P07-C — Staleness / Outlier / Sequence Checks

Task: `FIN-P07-WC-001`  
Linear: `HOS-205`  
State: CANONICAL_COMPLETE  
Lead: A2 Data  
Supporting: A0, A1, A4, A8, A9, A10

## Objective

Add deterministic integrity controls after P07-A/B without introducing hidden statistical heuristics.

## Staleness

Freshness is evaluated against a caller-supplied governed `reference_time_ns` and explicit per-kind limits for event age and receive age.

Future event/receive timestamps and missing freshness rules fail closed.

## Outlier checks

P07-C does not learn thresholds from the same batch. Numeric values are supplied as explicit observations and checked against governed rules:

- optional minimum;
- optional maximum;
- optional maximum absolute change from the previous observation of the same metric.

Missing rules for supplied observations fail closed.

## Sequence integrity

Sequence semantics are declared per canonical-id/provider stream.

- `NUMERIC_MONOTONIC_CONTIGUOUS`: parse as non-negative integer and detect duplicate, backward and gap states;
- `OPAQUE_NO_ORDER`: preserve the identifier as opaque and perform no ordering inference.

Missing sequence semantics or invalid numeric identifiers fail closed. Opaque identifiers are never coerced.

## Boundaries

Cross-provider divergence remains P07-D. Provenance/confidence fusion remains P07-E. Quarantine routing remains P07-F.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-C closure is canonical. P07-D is READY_NOT_STARTED under the existing P07 Owner authorization.

## Closure evidence

- Implementation PR: `#156` = MERGED
- Final implementation head: `5ca662aae12316627aef8d938f64cd073c180641`
- Implementation merge SHA: `2c35ef532eef3b66079c29294d5beac6d878b9d6`
- PR Governance: `37956164904` = SUCCESS
- PR artifact digest: `sha256:995b37368f580f03ec70174492ae47b3ff0729b0bc5df56b3f5c058de0b142ad`
- Post-merge Governance: `37956310206` = SUCCESS
- Post-merge artifact digest: `sha256:ecb877fa20355023fb02143452423a0892c1146ac023f06be7307a9f05311a2a`
- Post-merge Branch Hygiene: `37956310266` = SUCCESS
- Lock: RELEASED
- G5_TRUSTED_DATA: NOT_EVALUATED

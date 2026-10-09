# P07-C — Staleness / Outlier / Sequence Checks

Task: `FIN-P07-WC-001`  
Linear: `HOS-205`  
State: IN_PROGRESS  
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

P07-D remains blocked until P07-C canonical closure.

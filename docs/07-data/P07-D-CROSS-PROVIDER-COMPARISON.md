# P07-D — Cross-Provider Comparison

Task: `FIN-P07-WD-001`  
Linear: `HOS-206`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0, A1, A3, A4, A8, A9, A10

## Objective

Compare independent providers only when the data is explicitly aligned and semantically comparable.

## Comparison boundary

A group is defined by the exact tuple:

`sample_id + canonical_id + metric + comparison_family`

No comparison occurs across different families. A venue trade, broker/tick proxy, futures proxy, derived index or other semantically distinct source must use a different family unless governance explicitly proves equivalence.

## Coverage

Each observation carries `coverage_bps`. Each metric/family rule declares:

- minimum independent-provider count;
- minimum coverage per eligible observation;
- explicit absolute and/or relative divergence threshold.

Observations below minimum coverage do not satisfy the provider minimum. Insufficient eligible providers fail closed.

## Divergence

Eligible providers are sorted deterministically and compared pairwise. Absolute and relative divergence are evaluated independently against explicit thresholds.

## Boundaries

P07-E owns the canonical provenance/confidence and downstream eligibility contract. P07-F owns quarantine routing.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-E remains blocked until P07-D canonical closure.

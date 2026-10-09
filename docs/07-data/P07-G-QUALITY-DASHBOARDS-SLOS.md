# P07-G — Quality Dashboards & SLOs

Task: `FIN-P07-WG-001`  
Linear: `HOS-209`  
State: IN_PROGRESS  
Lead: A9 Operations  
Supporting: A0, A1, A2, A4, A8, A10

## Objective

Create deterministic vendor-neutral operational quality metrics and SLO evidence from P07-F routing outcomes.

## Metrics

For a governed observation window P07-G counts `ACCEPTED_DOWNSTREAM`, `QUARANTINED`, and `BLOCKED_UNKNOWN`, then derives exact integer basis-point rates using a 10,000 scale.

## SLO evaluation

Each SLO is versioned and declares one comparator:

- `MIN_GTE`: HEALTHY at/above objective, WARNING between objective and critical boundary, CRITICAL below the critical boundary.
- `MAX_LTE`: HEALTHY at/below objective, WARNING between objective and critical boundary, CRITICAL above the critical boundary.

An empty observation window returns `NO_DATA` for every SLO and is explicitly blocking.

## Dashboard snapshot

The reference implementation produces a content-addressed snapshot containing counts, rates, SLO evaluations, highest severity, blocking state and source decision evidence digests. No production observability or visualization vendor is selected.

## Boundaries

P07-H owns the integrated Trusted Data Gate / G5. P07-G does not enable trading.

## Safety

Production observability vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-H remains blocked until P07-G canonical closure.

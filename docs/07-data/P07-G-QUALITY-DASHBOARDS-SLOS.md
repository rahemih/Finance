# P07-G — Quality Dashboards & SLOs

Task: `FIN-P07-WG-001`  
Linear: `HOS-209`  
State: CANONICAL_COMPLETE  
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

P07-G closure is canonical. P07-H is READY_NOT_STARTED under the existing P07 Owner authorization.

## Closure evidence

- Implementation PR: `#164` = MERGED
- Final implementation head: `e43b30293e238f7d341c5ed37bbd07c45c5ae7e4`
- Implementation merge SHA: `7588dbd694c12f99b5e36e6fd2910dc5bf7c4b05`
- PR Governance: `37964366485` = SUCCESS
- PR artifact digest: `sha256:8878fc1becc37bb0fc64d69c83cab433a17bc5aaf27bcd44fcff59c43e5e3926`
- Post-merge Governance: `37964518957` = SUCCESS
- Post-merge artifact digest: `sha256:edba6b5fb4587549c406f4f8a03ec46d5b8b4478605dfeadabf736b16081a7e5`
- Post-merge Branch Hygiene: `37964519057` = SUCCESS
- Lock: RELEASED
- G5_TRUSTED_DATA: NOT_EVALUATED

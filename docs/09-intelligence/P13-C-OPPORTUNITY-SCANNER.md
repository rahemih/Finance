# P13-C — Opportunity Scanner

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WC-001`  
Linear: `HOS-263`  
Lock: `LOCK-FIN-P13-WC-001-01` / RELEASED

## Objective

Convert canonical P13-B timing assessments into a deterministic set of timing-context opportunity candidates without ranking them or granting trade authority.

## Canonical states

- `PREFERRED` / `STANDARD` → `ELIGIBLE_TIMING_CONTEXT`;
- `WEAK` → `OBSERVE_ONLY`;
- `INSUFFICIENT_EVIDENCE` / `CLOSED_CONTEXT` → `INELIGIBLE_CONTEXT`.

Every candidate carries a deterministic SHA-256 identity, asset/strategy/timeframe/regime/session context, P13-B timing class and explicit provenance/dataset lineage.

Output ordering is canonical and stable only. It is **not** opportunity ranking.

## Boundaries

- P13-D owns ranking;
- P13-E owns hard no-trade decisions;
- P13-F owns signal expiry/no-chase;
- P14 owns signal probability;
- no risk approval or execution authority;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #270 = MERGED
- implementation head `dcbdfceadd2fe0c2513e4666ca6ea4624458c9ff`
- implementation Governance `38372941946` = SUCCESS
- implementation artifact `sha256:5e75765661b0b0c257a5f75ca90a6e4bc36dc14e9d1bc9b660dfb9ef1096f107`
- implementation merge SHA `cdbde3d847d01db3c09ced315601f028a070c052`
- post-merge Governance `38373110107` = SUCCESS
- Branch Hygiene `38373110028` = SUCCESS
- implementation branch = DELETED
- P13-D = READY_NOT_STARTED

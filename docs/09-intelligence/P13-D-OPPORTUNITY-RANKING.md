# P13-D — Opportunity Ranking

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WD-001`  
Linear: `HOS-264`  
Lock: `LOCK-FIN-P13-WD-001-01` / RELEASED

## Objective

Rank eligible P13-C timing-context opportunities across assets/setups with a deterministic ordinal ordering while explicitly avoiding probability, hard no-trade authority, risk approval or execution.

## Canonical ordering

Only `ELIGIBLE_TIMING_CONTEXT` candidates are rankable.

Ordering is:
1. timing class priority: PREFERRED before STANDARD;
2. adjusted edge descending;
3. sample count descending;
4. candidate ID ascending.

The output is an ordinal `rank_position`; no probability/confidence score is emitted.

Non-eligible candidates are preserved only as excluded candidate IDs.

## Boundaries

- P13-E owns hard no-trade decisions;
- P13-F owns expiry/no-chase;
- P14 owns signal probability;
- P15/P16 own risk approval;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #272 = MERGED
- implementation head `ce8b796d4285c1c9cd9f84e45af0b74c7e39b663`
- implementation Governance `38374103096` = SUCCESS
- implementation artifact `sha256:1138c9f5dedfed00d7cb3f9b3971e848e7a4a9f69909f7f503fba397184baa43`
- implementation merge SHA `06483a5b36274c21284c47b601ab0055ebf7690c`
- post-merge Governance `38374276479` = SUCCESS
- Branch Hygiene `38374276764` = SUCCESS
- implementation branch = DELETED
- P13-E = READY_NOT_STARTED

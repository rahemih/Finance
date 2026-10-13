# P13-D — Opportunity Ranking

State: CLOSURE_RECONCILIATION  
Task: `FIN-P13-WD-001`  
Linear: `HOS-264`

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

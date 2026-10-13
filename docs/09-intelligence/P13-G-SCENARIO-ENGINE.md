# P13-G — Scenario Engine

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WG-001`  
Linear: `HOS-267`  
Lock: `LOCK-FIN-P13-WG-001-01` / RELEASED

## Objective

Frame deterministic conditional scenarios around canonical P13 timing/opportunity context without converting those scenarios into forecasts, probabilities, confidence scores, price targets, sizing decisions, risk approval or execution.

## Canonical model

For an upstream candidate that is both `TIMING_ELIGIBLE` and `ACTIVE`, the engine emits exactly three conditional frames:

1. `CONTINUATION` — current timing eligibility, validity and chase-limit conditions persist;
2. `DETERIORATION` — timing context weakens or data quality degrades;
3. `INVALIDATION` — a no-trade veto, expiry or no-chase condition invalidates the context.

For `EXPIRED`, `NO_CHASE` or `BLOCKED_BY_NO_TRADE`, the engine returns `NON_ACTIONABLE` and emits no actionable scenario frames.

Scenario IDs are deterministic SHA-256 identities over candidate, scenario kind and canonical condition codes.

## Boundaries

- scenarios are conditional frames, not probability;
- no confidence score;
- no price/return target;
- no position sizing;
- P13-H owns timing/ranking validation;
- P14 owns signal probability/calibration;
- P15/P16 own risk/sizing/approval;
- P20 owns execution.

## Safety

- upstream P13-E/F vetoes are non-bypassable;
- canonical tests are offline;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #278 = MERGED
- implementation head `2b03ff6f5ccd6161d8e9734b86a6c26f29802fab`
- implementation Governance `38383925579` = SUCCESS
- implementation artifact `sha256:8c74576a41d0ee1c2e73b1f51ea185527e4c03cc0d1356fe43d65a2db08024be`
- implementation merge SHA `429857262ae47b7295b678d4dad915b080543546`
- post-merge Governance `38384084395` = SUCCESS
- Branch Hygiene `38384084095` = SUCCESS
- implementation branch = DELETED
- P13-H = READY_NOT_STARTED

# P13-E — No-Trade Engine

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WE-001`  
Linear: `HOS-265`  
Lock: `LOCK-FIN-P13-WE-001-01` / RELEASED

## Objective

Implement the P13 No-Trade Guardian so the system can deterministically choose **no action** when timing/intelligence context is unsafe or unusable.

## Canonical hard-veto context

P13-E emits `NO_TRADE` when any governed reason is active:

- candidate is not eligible timing context;
- contradictory evidence;
- degraded data;
- high event risk;
- poor liquidity;
- excessive spread;
- stale evidence;
- extreme uncertainty.

If none are active and the candidate is canonically eligible, the result is `TIMING_ELIGIBLE`.

Reason codes use a deterministic policy order and preserve candidate identity.

## Ownership boundaries

P13-E consumes normalized context; it does not compute portfolio risk budgets or position sizing. Portfolio risk/capital preservation remains P15/P22 and independent pre-trade approval remains P16.

P13-F owns signal expiry/no-chase timestamp semantics. P14 owns signal probability.

## Safety

- no probability;
- no sizing;
- no portfolio-risk computation;
- no risk approval;
- no execution authority;
- canonical tests are offline;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #274 = MERGED
- implementation head `059e918d6cdad110cea45d114c91ad8e4044988e`
- implementation Governance `38375382619` = SUCCESS
- implementation artifact `sha256:5cc3c8958b02d408fbc954d2315cc8600fff75d0da2b41d986a76b84cda78487`
- implementation merge SHA `7b480d847b2303869220d2ef18acee93c5c66cb5`
- post-merge Governance `38375554474` = SUCCESS
- Branch Hygiene `38375554374` = SUCCESS
- implementation branch = DELETED
- P13-F = READY_NOT_STARTED

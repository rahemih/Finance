# P13-E — No-Trade Engine

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P13-WE-001`  
Linear: `HOS-265`

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

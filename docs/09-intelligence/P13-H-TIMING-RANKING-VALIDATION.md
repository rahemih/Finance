# P13-H — Timing / Ranking Validation

State: CLOSURE_RECONCILIATION  
Task: `FIN-P13-WH-001`  
Linear: `HOS-268`

## Objective

Perform an integrated deterministic validation across canonical P13-A through P13-G outputs before closing the Timing & Opportunity phase.

## Validation chain

The canonical validation bundle checks:

1. Session context ↔ timing assessment coherence;
2. timing assessment ↔ opportunity candidate identity and metrics;
3. opportunity ranking is contiguous, ordinal and eligible-only;
4. no-trade identity/reason semantics;
5. expiry/no-chase state cannot bypass upstream no-trade;
6. scenario actionability is coherent with expiry/no-chase state.

A valid bundle returns `PASS` plus the canonical six check codes. Any mismatch fails closed.

## Boundaries

P13-H validates existing P13 contracts. It does not introduce:
- probability or calibration;
- position sizing;
- portfolio risk;
- risk approval;
- execution authority.

## Safety

- canonical tests are offline;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

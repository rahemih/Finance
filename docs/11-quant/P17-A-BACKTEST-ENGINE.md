# P17-A — Backtest Engine

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WA-001`

## Objective

Provide the deterministic event-driven engine core for canonical P17 backtesting.

P17-A is an orchestration/accounting layer. It is deliberately **not** the final execution-realism model.

## Canonical inputs

The engine consumes:
- a P06 `ReplaySnapshot` identity and replay window;
- explicitly ordered market events;
- an injected strategy evaluator;
- an injected execution simulator;
- explicit initial cash and artifact identities.

The engine rejects a run when the run specification does not reference the exact replay snapshot used.

## Point-in-time rule

Every market event carries:
- `event_time_ns`;
- `available_at_ns`.

The engine requires:

`available_at_ns <= event_time_ns`

Events are processed in canonical sequence order. Decreasing simulated event time fails closed. P06 `ReplaySnapshot.view_at()` is invoked for each event, preserving the snapshot window/cutoff boundary.

The strategy receives only:
- the current market event;
- the current portfolio view.

No future event collection is passed into the strategy callback.

## Execution-simulation boundary

P17-A requires an injected `ExecutionSimulator`.

There is **no production simulator default** and no hidden zero-cost or immediate-fill assumption.

The simulator interface supports:
- fills released on later market events;
- immediate fills after a submitted decision;
- partial fills through repeated fill events.

The engine independently rejects:
- unknown-decision fills;
- duplicate fill IDs;
- fill direction inconsistent with the remaining decision;
- overfills;
- asset price-scale mismatch;
- a new decision that overlaps an unresolved decision for the same asset.

Fees, spread, slippage, funding, latency and partial-fill realism policy are owned by **P17-B**.

P17-A tests/evidence use a fixture-only immediate zero-cost simulator solely to prove deterministic engine mechanics.

## Accounting

The engine maintains deterministic:
- base-currency cash;
- signed per-asset positions;
- latest marks;
- mark-to-market equity;
- equity curve;
- unresolved simulated decisions.

A result with unresolved decisions is explicitly marked:

`COMPLETED_WITH_UNRESOLVED_DECISIONS`

rather than silently treating unresolved execution as complete.

## Authority boundary

P17-A does not:
- claim profitability;
- certify robust strategy validity;
- pass `G9_QUANT_VALIDATED`;
- connect to brokers/exchanges;
- route or execute orders;
- enable Demo/Shadow/Live progression.

AR-1 remains a separate cross-cutting Research Fast Track workstream. P17-A follows compatible deterministic/point-in-time principles but does not silently mark AR-1 complete.

P17-B..P17-I = NOT_STARTED.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

# P14-I — Signal Validation Gate

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P14-WI-001`  
Linear: SYNC_BLOCKED_FREE_ISSUE_LIMIT

## Objective

Validate the integrated P14 analytical signal chain and certify the frozen P14 exit gate:

`G7_SIGNAL_VALIDATED`

P14-I does not introduce a new trading model. It verifies that P14-H outputs are exactly reproducible from canonical P13/P14 inputs and that P14 safety boundaries remain intact.

## Per-signal validation

For every expected `AnalyticalSignalOutput`, P14-I:
- replays P14-H from the exact upstream candidate, timing guard, expiry/no-chase, fusion, probability, uncertainty, TP/Stop, Persian explanation and Red-Team inputs;
- requires exact `signal_id` match;
- requires exact canonical payload match;
- requires complete price geometry for LONG/SHORT;
- requires no price geometry for WAIT/NO_TRADE;
- verifies that risk approval, size, leverage and execution command remain absent.

Any mismatch fails closed.

## G7 phase certification

The deterministic phase-validation matrix requires exactly one validated certificate for each action:

- LONG
- SHORT
- WAIT
- NO_TRADE

Missing coverage, duplicate action coverage or any non-validated certificate fails closed.

Only complete validated coverage emits:

`G7_SIGNAL_VALIDATED / PASS`

## Phase boundary

Passing G7 closes P14 only. It does **not** start P15.

P15 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

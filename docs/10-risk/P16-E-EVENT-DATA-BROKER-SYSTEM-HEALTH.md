# P16-E — Event / Data / Broker / System Health Check

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P16-WE-001`

## Objective

Aggregate canonical health inputs into a final fail-closed health barrier before daily-loss, override and G8 checks.

## Inputs

Event:
- canonical P10-B economic calendar events;
- explicit governed block-before and block-after windows;
- explicit maximum observation age.

Data:
- canonical P07 Quality SLO state;
- only `HEALTHY` passes.

Broker / market-data path:
- P05 StreamHealth must be `HEALTHY`;
- P05 RecoveryState must be `ACTIVE`.

System:
- canonical system state must be `NORMAL`;
- `DEGRADED`, `SAFE_MODE`, `HALTED`, `EMERGENCY`, and `RECOVERY` veto new pre-trade admission.

## Event semantics

Cancelled events do not block.

For active events, the firewall blocks inside the governed pre/post release window. Stale or future-dated event observations fail closed.

## Boundary

Positive output is `PRETRADE_E_ELIGIBLE` only.

P16-F..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
No order-routing or execution authority exists here.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

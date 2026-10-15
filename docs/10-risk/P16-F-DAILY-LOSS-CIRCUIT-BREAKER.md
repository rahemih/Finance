# P16-F — Daily Loss / Circuit Breaker

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P16-WF-001`

## Objective

Fail closed when the governed daily-loss limit has been reached or a prior circuit trip remains latched.

## Inputs

- explicit caller-supplied `trading_day_id`;
- explicit day-start equity;
- current equity;
- explicit governed maximum daily-loss bps;
- prior circuit state: `CLEAR` or `TRIPPED`.

P16-F intentionally does not derive a timezone or trading-day boundary.

## Loss calculation

If current equity is greater than or equal to day-start equity, daily loss is zero.

Otherwise:

`daily_loss_bps = ceil((day_start_equity - current_equity) / day_start_equity * 10000)`

The circuit trips when daily loss is **greater than or equal to** the explicit governed limit.

Once `TRIPPED`, the circuit remains latched for this input state. Reset governance is outside P16-F and belongs to P16-G.

## Boundary

Positive output is `PRETRADE_F_ELIGIBLE` only.

P16-F does not reset circuits, close positions, produce G8, route orders or execute trades.

P16-G..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

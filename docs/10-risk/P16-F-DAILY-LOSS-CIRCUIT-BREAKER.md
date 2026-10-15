# P16-F — Daily Loss / Circuit Breaker

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- implementation PR #334 = MERGED;
- implementation head = `0f3f65a93a26793e7f10d7ec31199e4c1eb57bfc`;
- Governance `38735737224` = SUCCESS;
- artifact = `sha256:3a66660f397cbac42fbf1abd30691d6a606543c33b119218793429f6b268e28c`;
- implementation merge = `f2705f6e265fda71a85a5dde5856d0104a873f5e`;
- `FIN-P16-WF-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WF-001-01` = RELEASED;
- P16-G = READY_NOT_STARTED;
- P16-H = NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED.

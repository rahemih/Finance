# P15-E — Margin / Leverage

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WE-001`

P15-E measures the post-candidate leverage and margin utilization using explicit account and instrument inputs.

Metrics:
- leverage: gross notional / account equity, represented as milli-x;
- margin utilization: total margin used / account equity, represented in bps;
- candidate initial margin: candidate notional × explicit initial-margin rate.

All limits are explicit governed inputs. There is no default leverage such as 10×, 20× or any other production number.

Metrics use conservative ceiling rounding so risk is not understated.

A positive `MARGIN_LEVERAGE_ELIGIBLE` result is not execution approval.

P15-F..P15-I = NOT_STARTED.  
P16 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

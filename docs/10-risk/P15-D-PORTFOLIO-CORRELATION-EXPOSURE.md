# P15-D — Portfolio / Correlation Exposure

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WD-001`

P15-D evaluates portfolio-level concentration after P15-C.

It uses explicit governed limits for:
- gross exposure in bps of NAV;
- absolute net exposure in bps of NAV;
- absolute correlation threshold in milli-correlation;
- maximum gross exposure of a connected correlated cluster.

All distinct asset pairs require explicit correlation input. Unknown correlation fails closed.

`PORTFOLIO_ELIGIBLE` is not leverage approval and is not execution approval.

P15-E..P15-I = NOT_STARTED.  
P16 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

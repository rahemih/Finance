# P15-E — Margin / Leverage

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- PR #311 = MERGED;
- implementation head = `bed0e8ed98ea3cc45bddad57f53ff14525f50219`;
- Governance = `38528241794` / SUCCESS;
- artifact = `sha256:8a8aaffacec0559f42c689fcaf2d3b8cfb1665b64544dc2302ab091b9be108f1`;
- implementation merge = `5fcb7dc66bdfca259509f5a31899f6f68e366b59`;
- `FIN-P15-WE-001` = CANONICAL_COMPLETE;
- lock = RELEASED;
- P15-F = READY_NOT_STARTED;
- P15-G..P15-I = NOT_STARTED;
- P16 = NOT_STARTED.

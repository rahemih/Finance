# P15-F — Drawdown / Risk-of-Ruin

State: CANONICAL_COMPLETE  
Task: `FIN-P15-WF-001`

## Objective

Apply deterministic drawdown and risk-of-ruin controls after P15-E margin/leverage admission.

## Drawdown

Drawdown is computed from explicit peak and current equity and rounded upward in basis points so risk is never understated.

The policy requires two explicit governed thresholds:
- soft drawdown threshold;
- hard-stop drawdown threshold.

A soft breach emits `DE_RISK_REQUIRED`; a hard breach emits `VETO`.

## Risk of ruin

P15-F does not invent a production statistical model. It requires:
- an explicit ruin probability in parts per million;
- a non-empty validated `ruin_model_id`;
- an explicit governed maximum ruin probability.

A probability above the governed maximum emits `VETO`.

## Boundary

P15-H owns the defensive mode/scaling response to `DE_RISK_REQUIRED`.  
P15-G owns counterparty/capital segmentation.  
P15-I owns integrated validation.  
P16 remains NOT_STARTED.

No liquidation or broker/exchange order authority exists here.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #314 = MERGED;
- implementation head = `591f8a476aa84dadc075382dd43d494ad28d1ba5`;
- Governance `38531298706` = SUCCESS;
- artifact = `sha256:18ae003e66bfe34121030cd43443e6ebb25f75747231e3938195605d0630e244`;
- implementation merge = `e37180e2ee37bc99a181f33509e56aaba50a2e68`;
- `FIN-P15-WF-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P15-WF-001-01` = RELEASED;
- P15-G = READY_NOT_STARTED;
- P15-H..P15-I = NOT_STARTED;
- P16 = NOT_STARTED.

# P15-F — Drawdown / Risk-of-Ruin

State: IMPLEMENTATION_ACTIVE  
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

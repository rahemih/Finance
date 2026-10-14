# P15-H — Defensive / De-Risk Modes

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WH-001`

## Objective

Translate canonical P15 risk state into deterministic defensive **new-risk** modes.

Modes:
- `NORMAL` — 10000 bps of otherwise-allowed new risk;
- `REDUCED_RISK` — explicit governed reduced scale;
- `DEFENSIVE` — explicit governed defensive scale;
- `HALT_NEW_RISK` — 0 bps new risk.

The 10000 bps NORMAL value is semantic 100% of otherwise-governed risk, not a monetary risk limit.

## Precedence

Most restrictive condition wins:
1. upstream VETO or CRITICAL health → HALT_NEW_RISK;
2. P15-F DE_RISK_REQUIRED → DEFENSIVE;
3. DEGRADED data/counterparty health → REDUCED_RISK;
4. otherwise NORMAL.

## Boundary

This module does not close existing positions, liquidate, route orders or execute trades. It emits a policy directive for future risk admission only.

P15-I owns independent integrated validation.  
P16 remains NOT_STARTED.

Production scaling defaults: **NONE**.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

# P17-I — Benchmark / Quant Gate

State: CANONICAL_COMPLETE  
Task: `FIN-P17-WI-001`  
Frozen-roadmap gate: `G9_QUANT_VALIDATED`

## Objective

Provide the final independent quant-validation barrier for P17.

G9 requires:
- exact canonical evidence coverage for P17-A..P17-H;
- Strategy Registry identity;
- Model Registry identity;
- one passing governed criterion for each required benchmark category.

## Required benchmark categories

- `OOS_EDGE`
- `RISK`
- `ROBUSTNESS`
- `CAPACITY`
- `EXECUTION_REALISM`

Threshold values are explicit governed inputs. P17-I defines no production numeric defaults.

Supported comparisons:
- `GE` — measured value must be greater than or equal to threshold;
- `LE` — measured value must be less than or equal to threshold.

Any missing/duplicate category, missing/duplicate P17 evidence, failing criterion or invalid evidence identity fails closed.

## Positive result

The only positive phase-exit result is:

`G9_QUANT_VALIDATED / PASS`

This is quantitative validation, not a profitability guarantee and not permission to trade or start P18 automatically.

After PASS:
- P17 may close canonically;
- P18 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`;
- LIVE_TRADING remains DISABLED;
- AUTO_TRADING remains DISABLED.


## Canonical closure evidence

- implementation PR #358 = MERGED;
- implementation head = `45d3f5acb9e4eb23033e7857053318fc06767c05`;
- Governance `39009925612` = SUCCESS;
- artifact = `sha256:9a1ef4d26afcfd6a9952a9c0ce0d8f6f24aa7b781b646fecd5f6e5361860d4ea`;
- implementation merge = `0da38f07a7690ebafec1d407b875f2b3bd06eb3a`;
- `FIN-P17-WI-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P17-WI-001-01` = RELEASED;
- `G9_QUANT_VALIDATED` = PASS;
- P17 phase closure = READY;
- P18 = NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED.

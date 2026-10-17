# P17-I — Benchmark / Quant Gate

State: IMPLEMENTATION_ACTIVE  
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

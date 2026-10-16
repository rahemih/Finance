# P17-F — Liquidity / Capacity Testing

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WF-001`

## Objective

Measure how historical displayed liquidity behaves as the same baseline order is scaled upward under the exact P17-B displayed-depth participation policy.

## Inputs

P17-F consumes:
- P17-E robustness certificate lineage;
- P17-B `ExecutionRealismPolicy`;
- P17-B historical execution contexts with point-in-time depth;
- explicit baseline quantity;
- explicit scale points in basis points.

No production size scale is invented by P17-F.

## Probe semantics

For each historical context and each scale:
- requested quantity is derived from the baseline quantity;
- only the governed fraction of displayed depth may be consumed;
- fill ratio is measured;
- displayed capacity utilization is measured;
- adverse displayed-depth slippage is measured with conservative rounding;
- consumed depth levels are recorded.

The certificate aggregates worst-case diagnostics per scale and records the largest tested scale that fully fills across every supplied context.

## Important limits

P17-F makes **no hidden-liquidity inference** and **no true market-impact claim**. It measures only what the historical displayed book plus P17-B participation assumptions support.

A fixed probe-count ceiling prevents resource exhaustion. It is an execution-safety cap, not a financial threshold.

## Authority boundary

Output status is `CAPACITY_EVALUATED`, not a quant PASS.

P17-F has no:
- profitability-claim authority;
- G9 authority;
- strategy/model selection authority;
- execution or routing authority;
- production-promotion authority.

P17-G..P17-I remain later workstreams.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

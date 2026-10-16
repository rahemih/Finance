# P17-E — Monte Carlo / Stress / Sensitivity

State: CANONICAL_COMPLETE  
Task: `FIN-P17-WE-001`

## Objective

Measure robustness of the already-isolated P17-D OOS evidence without creating a profitability claim or selecting a model.

## Monte Carlo

P17-E uses a deterministic moving-block bootstrap over the chronological OOS return series.

Sampling is derived from:
- an explicit SHA-256 seed;
- path index;
- block index.

No environment RNG, random device, clock or implicit seed is used.

A fixed computational safety cap bounds total simulated observations to prevent resource-exhaustion. This is an execution-safety ceiling, not a financial threshold or production modeling default.

The governed input explicitly supplies:
- path count;
- path length;
- block size.

Diagnostics include:
- minimum terminal return;
- lower-tail (5%) terminal return;
- median terminal return;
- worst path max drawdown.

## Stress

Every stress scenario is explicit and identified by ID.

A scenario applies:
- additional loss shock in bps;
- additional cost drag in bps.

P17-E records terminal return and max drawdown under each scenario. It does not invent production stress values.

## Sensitivity

Sensitivity variants are explicit parameter-set artifacts with deterministic SHA-256 lineage and an externally computed evaluation metric.

P17-E records:
- minimum metric;
- maximum metric;
- dispersion;
- worst degradation from the declared baseline.

It does not optimize or select the best variant.

## Authority boundary

The output status is `ROBUSTNESS_EVALUATED`, not a profitability PASS.

P17-E has no:
- profitability-claim authority;
- candidate/model selection authority;
- G9 authority;
- execution or routing authority;
- production-promotion authority.

P17-F..P17-I remain later workstreams.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #350 = MERGED;
- implementation head = `c13236d5432337e1e3624236e99764ee4e61125a`;
- Governance `38932486210` = SUCCESS;
- artifact = `sha256:f2b0542cc9eb43139b22c7680446295988c7d41aefa66d1142479c5b585cb7e1`;
- implementation merge = `fbba261811d57fe0efae95b098d3ec9c3f011b1f`;
- `FIN-P17-WE-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P17-WE-001-01` = RELEASED;
- P17-F = READY_NOT_STARTED;
- P17-G..P17-I = NOT_STARTED;
- `G9_QUANT_VALIDATED` = NOT_REACHED.

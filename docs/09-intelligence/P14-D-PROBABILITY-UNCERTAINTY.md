# P14-D — Sample Size / Confidence Interval / Regime Similarity / Uncertainty

State: CANONICAL_COMPLETE  
Task: `FIN-P14-WD-001`  
Linear: `HOS-272`  
Lock: `LOCK-FIN-P14-WD-001-01` / RELEASED

## Objective

Qualify canonical P14-C empirical probabilities with transparent statistical and regime-context uncertainty without modifying the underlying probability.

## Statistical uncertainty

P14-D computes a deterministic 95% Wilson score confidence interval directly from the P14-C calibration cell's `success_count` and `sample_count`.

The empirical probability remains exactly the P14-C raw historical frequency. P14-D does not smooth, shrink, reweight or replace it.

Sample support is exposed as:
- `MINIMUM` below 20 observations;
- `MODERATE` from 20 through 49 observations;
- `STRONG` at 50 or more observations.

These labels are evidence-support metadata, not probability.

## Regime similarity

Regime similarity must arrive as explicit governed evidence bound to the exact P14-C prediction. Canonical allowed sources are:
- `P12_HISTORICAL_ANALOG`;
- `P08_REGIME`.

The evidence carries similarity, its own uncertainty, source record identity and SHA-256 provenance. Similarity is never interpreted as probability.

## Conservative overall uncertainty

The canonical uncertainty components are:
- Wilson interval half-width;
- regime dissimilarity = `10000 - similarity_bps`;
- upstream regime-evidence uncertainty.

`overall_uncertainty_bps` is the maximum component, preserving a conservative fail-closed posture. Dominant component names are emitted explicitly.

If P14-C has insufficient calibration data, P14-D does not invent a probability or confidence interval and returns maximum uncertainty.

## Boundaries

- P14-E owns TP/Stop outcome probabilities;
- P14-F owns Persian explainability;
- P14-G owns independent Red-Team challenge;
- P14-H owns signal output contract;
- P14-I owns G7 validation;
- no risk sizing/approval or execution authority;
- LLM probability/uncertainty authority = FORBIDDEN;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #289 = MERGED
- implementation head `4da9199f63474384a9ce8a4cc645ec41cb1c037d`
- implementation Governance `38402854339` = SUCCESS
- implementation artifact `sha256:118e0fb5fb52879befc5c3604546b97d4fb74e527f44491009799a9658f1dc5c`
- implementation merge SHA `da080df9d91c9a0e88fa3124f0f4a1919925a2ab`
- post-merge Governance `38403079903` = SUCCESS
- Branch Hygiene `38403079751` = SUCCESS
- implementation branch = DELETED
- P14-E = READY_NOT_STARTED

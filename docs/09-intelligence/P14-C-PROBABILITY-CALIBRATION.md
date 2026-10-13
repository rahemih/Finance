# P14-C — Probability / Calibration Engine

State: CLOSURE_RECONCILIATION  
Task: `FIN-P14-WC-001`  
Linear: `HOS-271`

## Objective

Turn canonical P14-B directional FUSED evidence scores into an empirical historical success probability without lookahead and without allowing an LLM to invent probabilities.

## Calibration contract

Calibration is scoped to one exact:
- subject;
- strategy;
- timeframe;
- regime;
- session;
- versioned outcome definition.

Historical observations preserve the signed fusion score, fused direction, success label, decision as-of time, outcome-observed time, source dataset version and provenance.

Every outcome used for training must already be observed by the model training cutoff. Prediction as-of must be strictly later than that cutoff.

## Probability semantics

The canonical baseline uses governed absolute score bands and raw empirical frequency only:

`probability_bps = round(success_count × 10000 / sample_count)`

No synthetic prior or smoothing is applied. If the selected calibration cell has fewer than the governed minimum samples, state is `INSUFFICIENT_CALIBRATION_DATA` and probability is null.

## Boundaries

- P14-D owns confidence intervals, sample-size uncertainty and regime similarity;
- P14-E owns TP/Stop outcome probabilities;
- P14-F owns Persian explanation;
- P14-G owns independent challenge;
- no risk sizing/approval or execution authority;
- LLM probability authority = FORBIDDEN;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

# P14-C — Probability / Calibration Engine

State: CANONICAL_COMPLETE  
Task: `FIN-P14-WC-001`  
Linear: `HOS-271`  
Lock: `LOCK-FIN-P14-WC-001-01` / RELEASED

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


## Canonical closure evidence

- implementation PR #287 = MERGED
- implementation head `23487ad14e9b543588f12f0df92e7b1b86fdc982`
- implementation Governance `38400858778` = SUCCESS
- implementation artifact `sha256:8d2200c73b700091608d938b569cd188756b2faf2f41cbd7fc75a1c7fc151710`
- implementation merge SHA `7074172aa98ef300ed71cc901b0f0d00f30026af`
- post-merge Governance `38401049568` = SUCCESS
- Branch Hygiene `38401049434` = SUCCESS
- implementation branch = DELETED
- P14-D = READY_NOT_STARTED

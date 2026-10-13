# P14-E — TP / Stop Outcome Probabilities

State: CLOSURE_RECONCILIATION  
Task: `FIN-P14-WE-001`  
Linear: `HOS-273`

## Objective

Estimate historical outcome-specific probabilities for one exact candidate TP/Stop plan without inventing price paths and without crossing into portfolio risk, order execution or position management.

## Outcome contract

One calibration context fixes:
- subject;
- strategy;
- timeframe;
- regime;
- session;
- direction;
- target distance in basis points;
- stop distance in basis points;
- evaluation horizon;
- versioned outcome definition.

Admissible historical labels are mutually exclusive:

- `TP_FIRST`
- `STOP_FIRST`
- `NEITHER`

Ambiguous or unresolved path labels are rejected. P14-E does not infer which barrier was touched first from ambiguous data.

Every outcome used in training must already be observed by the training cutoff.

## Probability semantics

For sufficient historical support, the three outcome probabilities are raw empirical frequencies and are deterministically rounded so their distribution sums to exactly 10000 basis points.

The general empirical directional-success probability from P14-C/P14-D remains separate context. It is not required to equal `TP_FIRST` probability because the definitions are different.

If P14-D is insufficient, P14-E returns `INSUFFICIENT_UPSTREAM_CALIBRATION` with no outcome probabilities.

If the TP/Stop dataset itself is below the governed minimum, P14-E returns `INSUFFICIENT_TP_STOP_DATA`.

## Boundaries

- no synthetic prior or smoothing;
- no LLM probability authority;
- P14-F owns Persian explanation;
- P14-G owns independent challenge;
- P14-H owns final signal output contract;
- P14-I owns G7 validation;
- P15 owns portfolio risk / sizing;
- P16 owns independent pre-trade approval;
- P20/P21 own execution and position management;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

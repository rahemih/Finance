# P08-C — Momentum Family

Task: `FIN-P08-WC-001`
Linear: `HOS-213`
Lock: `LOCK-FIN-P08-WC-001-01`
State: IMPLEMENTATION_ACTIVE

## Objective

Implement a deterministic point-in-time Momentum Family distinct from P08-B Trend.

## Model

The reference family uses short-horizon rate of change, long-horizon rate of change, and horizon-normalized acceleration. These correlated measurements are one family under `return-momentum`, not multiple independent confirmations.

The family emits one `TechnicalEvidence` object with bullish, bearish, or neutral direction.

## Controls

Inputs must share symbol, timeframe, dataset version, and data-quality lineage; event times are strictly increasing and future as-of information is rejected.

Strength and confidence are deterministic technical-evidence scores, not empirical trade probabilities.

## Safety

Direct trade output is forbidden. Live Trading and Auto Trading remain DISABLED. Country assumption is NONE. No network or credentials are required.

## Boundary

P08-D and later workstreams remain out of scope. G6 is not evaluated here.

# P08-G — Multi-Timeframe & Regime

Task: `FIN-P08-WG-001`  
Linear: `HOS-221`  
Lock: `LOCK-FIN-P08-WG-001-01`  
State: IMPLEMENTATION_ACTIVE

## Objective

Implement the canonical `EF_REGIME_MULTI_TIMEFRAME` baseline as one deterministic REGIME-family evidence object describing compatibility of the same TREND method across multiple observation timeframes.

## Architecture rule

Multiple timeframes of the same method are **related evidence, not independent confirmations**.

P08-G therefore does not count 15m, 1h and 4h Trend as three votes. It consumes the governed Trend family snapshots and emits one REGIME evidence object.

## Classification

For one symbol and one evaluation clock:

- all bullish Trend snapshots → `ALIGNED_BULLISH`;
- all bearish → `ALIGNED_BEARISH`;
- all neutral → `NEUTRAL`;
- bullish and bearish both present → `CONFLICT`;
- one directional sign plus neutral snapshots → `TRANSITION`.

Only the two fully aligned states carry bullish/bearish REGIME direction. Transition, Conflict and Neutral remain direction zero.

## Conservative score semantics

For aligned states:

- strength = deterministic average of constituent Trend strength;
- confidence = minimum constituent Trend confidence.

This prevents adding timeframes from mechanically inflating confidence.

For non-aligned states, strength and confidence remain zero; disagreement is classification context, not evidence strength.

## Point-in-time / provenance invariants

P08-G fails closed unless constituent snapshots have:

- unique timeframe labels;
- the same symbol;
- the same evaluation `as_of_time_ns`;
- the same Trend method definition and Trend independence group;
- the same source dataset version and quality-evidence lineage.

Input ordering is canonicalized and cannot change the output evidence identity.

## Independence boundary

- cross-timeframe status: `RELATED_NOT_INDEPENDENT`;
- cross-family status: `PROVISIONAL_PENDING_P08_H`;
- formal technical dependence/correlation certification remains P08-H.

## Score semantics

Strength/confidence are deterministic evidence scores. They are not trade-success probability, calibrated signal probability, position sizing, risk approval or execution authority.

## Safety

- Direct trade/order output: FORBIDDEN
- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Network/credentials required: NO

## Boundary

P08-H and P08-I remain separate. AR-0 remains READY_NOT_STARTED while P08-G owns shared reconciliation paths.

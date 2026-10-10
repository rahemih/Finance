# P08-G — Multi-Timeframe & Regime

Task: `FIN-P08-WG-001`  
Linear: `HOS-221`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

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


## Canonical closure evidence

- Implementation PR: `#182` = MERGED
- Final implementation head: `c74fdfec54e151a5cb118d0ef9364a526884be25`
- Implementation merge SHA: `860c4b4ed05938b05a7eb6e67edf52c1b4c60e6a`
- PR Governance: `38043070756` = SUCCESS
- PR artifact: `sha256:5998e726a5f7f9a3c1adf22bd20758ad91c9e88aba8e66972b28b590993dc16a`
- Post-merge Governance: `38043140519` = SUCCESS
- Post-merge artifact: `sha256:806691516a802e7a0e81654b7c0ac43f3d095690c37435953fc4af230aa19d9a`
- Post-merge Branch Hygiene: `38043140522` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-G evidence: PASS
- Multi-timeframe copies remain RELATED_NOT_INDEPENDENT
- Cross-family independence remains PROVISIONAL_PENDING_P08_H

P08-H — Independence / Correlation Audit is READY_NOT_STARTED. AR-0 — Research Governance is READY_NOT_STARTED under separate cross-cutting ownership.

# P08-B — Trend Family

Task: `FIN-P08-WB-001`  
Linear: `HOS-212`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Implement a deterministic, point-in-time Trend Family on top of the canonical P08-A technical evidence contract.

## Model

The reference family evaluates three correlated properties of the same price path:

1. fast-vs-slow moving-average alignment;
2. slow-baseline slope over a governed offset;
3. current price distance from the slow baseline.

These inputs are deliberately treated as **one family model** under `price-path-trend`. They do not receive three independent confirmation votes.

The family emits one `TechnicalEvidence` object with direction:

- `1` = bullish trend evidence;
- `-1` = bearish trend evidence;
- `0` = neutral/ambiguous.

## Point-in-time and lineage controls

The required window must have:

- one symbol;
- one timeframe;
- one dataset version;
- one data-quality evidence lineage;
- strictly increasing event times;
- no input whose as-of time exceeds the evaluation as-of time.

Any violation fails closed.

## Score semantics

`strength_bps` and `confidence_bps` are deterministic technical-evidence scores. They are **not empirical win probabilities, TP probabilities, trade recommendations or risk approvals**. Probability calibration belongs to later roadmap phases.

## Safety

- Direct trade/order output: FORBIDDEN
- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Network/credentials required: NO

## Boundary

P08-C Momentum and all later P08 workstreams remain out of scope. G6 is not evaluated here.


## Canonical closure evidence

- Implementation PR: `#170` = MERGED
- Final implementation head: `6f772b2d65ca573955ddae17213f3d1d06273404`
- Implementation merge SHA: `146179db5b3d613fac97c890f0c6983a1f575629`
- PR Governance: `38035626597` = SUCCESS
- PR artifact: `sha256:f7c9bc8a2db7307152768f2e030c76250d606f1fd5f51a8ced658eeecddcfc19`
- Post-merge Governance: `38035702876` = SUCCESS
- Post-merge artifact: `sha256:dc629cfc4034b5dd0566b822cc610508b0510ce17d3cd673b912ab1f3bd5929d`
- Post-merge Branch Hygiene: `38035702947` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-B trend evidence: PASS

P08-C — Momentum Family is READY_NOT_STARTED. G6 remains NOT_EVALUATED.

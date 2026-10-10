# P08-B — Trend Family

Task: `FIN-P08-WB-001`  
Linear: `HOS-212`  
Lock: `LOCK-FIN-P08-WB-001-01`  
State: IMPLEMENTATION_ACTIVE

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

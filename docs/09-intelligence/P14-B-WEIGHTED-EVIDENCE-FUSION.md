# P14-B — Weighted Evidence Fusion

State: CLOSURE_RECONCILIATION  
Task: `FIN-P14-WB-001`  
Linear: `HOS-270`

## Objective

Combine canonical P14-A evidence deterministically while preserving independence, freshness and non-bypassable veto semantics. The fused score is an evidence score, **not** a calibrated trade probability.

## Fusion model

1. Any upstream hard veto returns `BLOCKED` immediately.
2. Expired evidence is excluded from fusion but its identity remains recorded.
3. Evidence is grouped by `independence_group`; one group contributes at most one representative.
4. Representative selection is deterministic: highest absolute quality-adjusted strength, then lowest evidence ID.
5. Per-representative signed contribution is:
   `direction × round(strength_bps × quality_bps / 10000)`.
6. Fusion score is the signed integer average across independent representatives.
7. `FUSED` requires at least 3 directional independent groups and at least 2 source families; otherwise state is `INSUFFICIENT_EVIDENCE`.

There are no arbitrary family-prior weights. LLMs cannot set weights.

## Boundaries

- fusion score is not probability or confidence;
- P14-C owns empirical probability/calibration;
- P14-D owns sample-size/confidence-interval/regime-similarity uncertainty;
- P14-E owns TP/Stop outcome probabilities;
- no portfolio risk, sizing, risk approval or execution authority;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

# P14-B — Weighted Evidence Fusion

State: CANONICAL_COMPLETE  
Task: `FIN-P14-WB-001`  
Linear: `HOS-270`  
Lock: `LOCK-FIN-P14-WB-001-01` / RELEASED

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


## Canonical closure evidence

- implementation PR #285 = MERGED
- implementation head `29087b7398482044c55850e81991de7fe120e6e4`
- implementation Governance `38396954193` = SUCCESS
- implementation artifact `sha256:3dec72d337c733d2a67974d50f605cc393bbf98910f6c909d50a321ac2bbdde5`
- implementation merge SHA `b168d7ae5b4d70fa8806e4e25a14672776537bfb`
- post-merge Governance `38397128341` = SUCCESS
- Branch Hygiene `38397128088` = SUCCESS
- implementation branch = DELETED
- P14-C = READY_NOT_STARTED

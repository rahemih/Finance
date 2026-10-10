# AR-0 — Research Governance

Task: `FIN-P08-WJ-003`  
Linear: `HOS-222`  
Lock: RELEASED  
State: CANONICAL_COMPLETE  
Protocol: `arft-research-protocol-v1`

## Objective

Freeze the generic rules that make later Alpha Research Fast Track experiments comparable, falsifiable, point-in-time safe, reproducible and auditable.

AR-0 governs research. It does not validate a technical family, calibrate a trade probability, approve Risk, or create execution authority.

## Frozen generic protocol

The following principles are frozen for AR-1 through AR-5:

- versioned code/library is authoritative; notebooks are exploration/visualization aids only;
- every experiment has machine-readable inputs, outputs and evidence;
- dataset/version references are immutable;
- point-in-time uncertainty fails closed;
- exploratory selection/tuning is separated from protected confirmation;
- search-space / hypothesis multiplicity is recorded;
- candidate-specific hypotheses are frozen only before confirmatory access, not invented in AR-0;
- unsupported numeric thresholds remain `TO_BE_CALIBRATED`;
- negative evidence may reject early;
- positive Fast Track evidence can retain a candidate for deeper validation but cannot pass canonical gates.

## Required AR-0 artifacts

Machine-readable governance:

- `ar0-research-governance.json`
- `point-in-time-safety-contract.json`
- `dataset-access-boundary.json`
- `exploratory-confirmatory-split-policy.json`
- `metric-registry.json`
- `candidate-decision-vocabulary.json`
- `regime-universe-methodology.json`

Schemas:

- `schemas/arft-evidence-envelope.schema.json`
- `schemas/confirmatory-hypothesis-contract.schema.json`

Tooling plan:

- `TOOL-BUILD-VS-BUY-ADR-PLAN.md`

Specialist authority:

- canonical `docs/09-agents/specialists/RESEARCH-VALIDATION-SPECIALIST.json`

## Point-in-time safety

A generic lag such as `shift(1)` is not evidence of safety.

Every candidate must establish, where applicable:

- event time;
- source information/publication availability time;
- provider receive/ingestion time;
- feature availability time;
- evaluation/decision clock;
- label horizon;
- dataset snapshot/version;
- revision/vintage identity;
- timezone/clock semantics;
- overlapping-label policy;
- purge and embargo policy.

For revised macro/fundamental data, only the vintage available at the historical decision time is eligible.

Unknown or unprovable availability produces `BLOCKED`.

## Data access and exploratory / confirmatory separation

`EXPLORATORY` data may be used in AR-1/AR-2 under a recorded search ledger.

`CONFIRMATORY_PROTECTED` data is inaccessible until the candidate-specific Confirmatory Hypothesis Contract is frozen with definition, parameters, target, hypothesis, metric family, asset methodology, holdout, regime taxonomy, decision procedure and dataset/partition references.

Premature or repeated protected-outcome access contaminates the partition. A contaminated partition is retired from confirmation and versioned as research-visible.

The evaluator cannot mutate the candidate after viewing confirmatory outcomes.

## Statistical safety

The protocol explicitly tracks:

- lookahead and data leakage;
- label/temporal contamination;
- survivorship and selection bias;
- data snooping and p-hacking;
- multiple testing/search multiplicity;
- parameter mining;
- regime and asset-specific overfitting;
- repeated holdout peeking.

Negative controls must use a candidate/metric-appropriate empirical null or permutation model. A non-zero shuffled result is not automatically labeled leakage.

No universal p-value, sample count, correlation, Monte Carlo count, fold count or asset cutoff is frozen here.

## Metrics

The metric registry is multidimensional rather than a mandatory weighted composite.

Safety preconditions can block an experiment. Statistical/context metrics then describe evidence, uncertainty and limitations. Candidate-specific thresholds require governed empirical calibration.

Pairwise correlation alone cannot establish redundancy or independence. Incremental-information analysis may use dependence measures, ablation, nested baselines or other governed methods appropriate to the candidate.

Formal technical cross-family independence remains P08-H/G6.

## Candidate decisions

Candidate research decisions are restricted to:

- `REJECT`
- `RETAIN_FOR_CONFIRMATION`
- `RETAIN_FOR_P17`
- `INVESTIGATE`

Fast Track never emits production validation, BUY/SELL, Risk approval or execution approval.

## Regime and universe methodology

BTC may be the reference development asset, but the Fast Track is BTC-first rather than BTC-only.

The sanity universe is selected ex ante using governed dimensions such as data/lineage quality, liquidity, history, comparability, structural diversity, dependency clusters and survivorship coverage.

Assets cannot be swapped after viewing candidate results merely to improve performance.

Regime taxonomy/version is frozen before confirmatory access. Numeric regime boundaries remain `TO_BE_CALIBRATED` until supported by governed evidence.

Cross-asset sanity and temporal holdout are separate dimensions; neither equals production generalization.

## Research Validation Specialist

The existing Research Validation Specialist remains a bounded on-demand specialist under A4.

AR-0 relies on its canonical authority boundary:

- independent reject/retain/investigate decisions within task scope;
- builder/evaluator separation;
- point-in-time and contamination review;
- no production/gate/risk/execution authority;
- no candidate mutation to rescue a failed confirmatory result.

A10 independently reviews evidence integrity; A0 resolves workflow conflicts without converting research evidence into a gate pass.

## Tool selection

Tool choice is `TO_BE_DECIDED_BY_ADR`.

AR-1 must run the Build-vs-Buy technology spike defined in `TOOL-BUILD-VS-BUY-ADR-PLAN.md`. Research, robustness/statistics and future event-driven simulation may use different layers.

## Gate and safety boundary

AR-0 does not change:

- P08-H/P08-I/G6 ownership;
- P14/G7 probability/fusion authority;
- P15/P16/G8 Risk authority;
- P17/G9 robust strategy validation;
- later Demo/Shadow/Live promotion.

Live Trading = DISABLED.  
Auto Trading = DISABLED.  
Country assumption = NONE.

## Exit

AR-0 may close only when:

- all required artifacts are versioned;
- schemas and policy references pass deterministic CI validation;
- unsupported thresholds remain unresolved/calibration-governed rather than arbitrary;
- the Research Validation Specialist boundary validates;
- Governance and post-merge verification pass;
- A10 review is represented by the deterministic evidence package and canonical governance checks.

After canonical closure, AR-1 becomes READY_NOT_STARTED.


## Canonical closure evidence

- Implementation PR: `#184` = MERGED
- Final implementation head: `40a5db1350cf8163f9194165235f2361b48becfb`
- Implementation merge SHA: `604699377faad33599359fa97d2895808ab56a82`
- PR Governance: `38043790412` = SUCCESS
- PR artifact: `sha256:ea88537f24e76ac10cc8da37e9812c7460ff7d35ce31b9b10215e74dd32974f9`
- Post-merge Governance: `38044124825` = SUCCESS
- Post-merge artifact: `sha256:5d991dec926d57eabfe4a6fff46dc06f6127c475b74e1786c18288c785336a26`
- Post-merge Branch Hygiene: `38044124795` = SUCCESS
- AR-0 deterministic research-governance evidence twice: PASS
- Research Validation Specialist authority validation: PASS
- unsupported numeric thresholds remain `TO_BE_CALIBRATED`
- Master Roadmap v2.0 remains FROZEN and unchanged

AR-1 — Reproducible Research Harness is READY_NOT_STARTED. P08-H — Independence / Correlation Audit remains READY_NOT_STARTED under the canonical P08 path.

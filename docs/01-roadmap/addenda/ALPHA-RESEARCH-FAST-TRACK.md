# NEXUS QUANT — Roadmap Addendum AR-FT-001
## Alpha Research Fast Track

STATE = PROPOSED_CANONICALIZATION  
BASELINE = `docs/01-roadmap/MASTER-ROADMAP-v2.0.md`  
BASELINE_STATE = FROZEN / UNCHANGED  
TASK = `FIN-P08-WJ-001`  
LINEAR = `HOS-219`  
LIVE_TRADING = DISABLED  
AUTO_TRADING = DISABLED  

## 1. Purpose

This addendum adds a research-only Alpha Research Fast Track (AR-FT) beginning during P08.

Its purpose is narrow:

> reject weak intelligence candidates earlier, preserve promising candidates for later canonical validation, and shorten the empirical feedback loop without weakening governance or turning the Fast Track into a hidden Strategy Factory.

The Fast Track is a cross-cutting research control. It is not a new production phase and it does not replace any canonical phase or gate.

## 2. Authority hierarchy

If documents conflict, authority remains:

1. `MASTER-ROADMAP-v2.0.md`
2. approved ERRATA / ADR / RFC / ROADMAP ADDENDUM
3. governed roadmap companions
4. Task Contracts and operational state

This addendum MUST NOT mutate the frozen Master Roadmap.

## 3. Non-negotiable boundaries

The Fast Track MAY:

- screen research candidates;
- falsify weak hypotheses early;
- compare candidates against governed baselines and empirical nulls;
- produce reproducible research evidence;
- classify candidates as `REJECT`, `RETAIN_FOR_CONFIRMATION`, `RETAIN_FOR_P17`, or `INVESTIGATE`;
- provide evidence to P08/P09/P10/P11/P12/P13/P14 and later P17.

The Fast Track MUST NOT:

- pass or substitute G6, G7, G8 or G9;
- claim a candidate is production validated;
- claim profitability;
- issue BUY/SELL execution instructions;
- approve risk;
- interact with broker/exchange order endpoints;
- promote any model/strategy to Demo, Shadow or Live;
- change the Research → Backtest → Demo → Shadow → Manual/Semi-Auto → Micro-Capital/Canary → Controlled Auto sequence;
- create a permanent core agent merely to operate the Fast Track.

Positive Fast Track evidence is asymmetric:

> strong negative evidence may eliminate a candidate early; strong positive evidence only justifies deeper canonical validation.

## 4. Relationship to canonical roadmap

| Area | Fast Track MAY establish | Fast Track MUST NOT establish | Canonical owner/gate |
|---|---|---|---|
| P08 Technical Intelligence | empirical usefulness, instability, redundancy warnings, point-in-time validity | G6 PASS or final independence certification | P08 / G6 |
| P14 Signal / Probability | candidate research inputs and limitations | signal fusion validity, calibrated trade probability, G7 PASS | P14 / G7 |
| P15/P16 Risk | research metadata usable later by Risk | risk approval, position sizing approval, G8 PASS | P15/P16 / G8 |
| P17 Strategy Factory | candidate intake evidence and falsification findings | robust strategy/backtest validation, execution realism, G9 PASS | P17 / G9 |
| P18+ | research context only | Demo/Shadow/Live promotion | canonical later phases |

Research evidence is not production validation.

## 5. Operating model

The Fast Track is gate-based, not calendar-based.

`AR-0 → AR-1 → AR-2 → AR-3 → AR-4 → AR-5`

### AR-0 — Research Governance

Objective:
freeze the rules that make later experiments comparable and auditable.

Required outputs:

- research protocol;
- point-in-time safety contract;
- dataset access boundaries;
- experimental/confirmatory split policy;
- metric definitions;
- candidate decision vocabulary;
- evidence schema;
- tool Build-vs-Buy ADR plan;
- Research Validation Specialist contract;
- regime and universe selection methodology.

Rules:

- generic protocol is frozen here;
- candidate-specific hypotheses are NOT pre-registered here because they may not exist yet;
- numerical thresholds with no governed empirical basis MUST be marked `TO_BE_CALIBRATED`;
- arbitrary sample-count, correlation, Monte Carlo, fold or asset-selection cutoffs are forbidden.

Exit:
AR-0 artifacts are versioned, schema-valid, non-conflicting with the Master Roadmap and independently reviewed by A10.

### AR-1 — Reproducible Research Harness

Objective:
provide a deterministic, testable computation source of truth.

Required properties:

- versioned code/library is authoritative;
- notebooks are limited to exploration, visualization and interpretation;
- experiment inputs and outputs are machine-readable;
- deterministic seeds and environment versions are recorded;
- dataset versions are immutable references;
- clean rerun is supported;
- experiment artifacts are content-addressed where practical;
- point-in-time availability is enforceable.

AR-1 does not require selecting one universal framework.

Tool choice remains:

`TO_BE_DECIDED_BY_ADR`

The ADR/technology spike must evaluate research, robustness and future event-driven simulation as potentially different tool layers.

Exit:
a governed reference experiment can be reproduced from its evidence envelope without hidden notebook state.

### AR-2 — Exploratory Feature Screening

Objective:
discover whether a candidate deserves confirmatory testing.

Allowed:

- exploratory transformations;
- governed metric analysis;
- empirical-null and negative-control tests;
- baseline comparisons;
- stability diagnostics;
- redundancy/incremental-information analysis;
- parameter sensitivity exploration inside the declared exploratory budget.

Forbidden:

- reading the protected confirmatory outcome set;
- final retention for P17;
- profitability claims;
- production validation claims;
- tuning against confirmatory results.

Outputs:

- `REJECT`;
- `RETAIN_FOR_CONFIRMATION`;
- `INVESTIGATE`.

Any candidate retained from AR-2 must create a Confirmatory Hypothesis Contract before AR-3 access.

### AR-3 — Confirmatory Cross-Asset / Regime Test

Objective:
test the frozen candidate hypothesis against evidence not used for exploratory selection/tuning.

Before access, freeze:

- feature definition;
- parameters;
- label definition;
- candidate hypothesis;
- metric family;
- asset-selection methodology;
- temporal holdout definition;
- regime taxonomy/version;
- decision rule or calibration procedure;
- confirmatory dataset references.

The evaluator MUST NOT change the frozen candidate after viewing confirmatory outcomes.

AR-3 must separate:

- cross-asset sanity;
- temporal holdout;
- regime-conditioned behavior;
- production-grade generalization.

Only the first three belong to Fast Track. Production-grade generalization remains P17.

Outputs:

- `REJECT`;
- `RETAIN_FOR_P17`;
- `INVESTIGATE`;
- warning/limitation metadata.

### AR-4 — Independent Candidate Retention

Objective:
make the research-retention decision without builder self-approval.

Authority:
Research Validation Specialist (RVS) has independent `REJECT` authority within this Task Contract boundary.

A3/A4 builders may provide methodology context but cannot override a valid RVS rejection by editing the evidence after the decision.

A10 verifies evidence integrity and governance compliance.

A0 resolves workflow conflicts but does not transform research evidence into a gate pass.

No single weighted composite score is required by default.

Preferred decision structure:

1. Safety Preconditions
2. Statistical Evidence
3. Context / Utility Evidence
4. Limitations / uncertainty
5. Decision with traceable rationale

A composite score may be introduced later only through a governed calibration artifact demonstrating that aggregation is useful and non-misleading.

### AR-5 — Falsification-Oriented Robustness Preview

Objective:
attempt to break a retained candidate before spending full P17 effort.

Boundary is defined by claim authority, not arbitrary test counts.

AR-5 MAY:

- run limited robustness diagnostics;
- perturb parameters and assumptions;
- run simple cost/turnover sensitivity where relevant;
- look for sign instability, regime collapse or dependence on fragile assumptions;
- reject candidates that fail clearly.

AR-5 MUST NOT:

- certify profitability;
- perform canonical Walk-Forward validation;
- replace P17 Monte Carlo/stress/capacity validation;
- perform execution-grade fill/slippage realism as a final claim;
- optimize a full strategy stack;
- promote a model or strategy.

Allowed inference:

- strong negative evidence → `REJECT`;
- inconclusive evidence → `INVESTIGATE`;
- strong positive evidence → `RETAIN_FOR_P17` only.

## 6. Point-in-Time Safety Contract

Every candidate experiment must preserve and validate, where applicable:

- event time;
- source publication/information-availability time;
- provider receive/ingestion time;
- feature availability time;
- decision/evaluation time;
- label horizon;
- revision/vintage identity;
- dataset snapshot/version;
- timezone/clock semantics;
- overlapping-label policy;
- purge policy;
- embargo policy.

A generic `shift(1)` rule is insufficient evidence of lookahead safety.

A feature is point-in-time safe only if the harness can establish that every consumed value was available under the declared decision clock before the evaluated outcome horizon.

Macro/fundamental/revised data MUST use the vintage that was actually available at the relevant historical time.

Point-in-time uncertainty fails the experiment closed.

## 7. Statistical safety model

The Fast Track explicitly controls:

- lookahead bias;
- data leakage;
- label leakage;
- temporal contamination;
- survivorship bias;
- selection bias;
- data snooping;
- multiple-hypothesis testing;
- p-hacking;
- parameter mining;
- regime overfitting;
- asset-specific overfitting;
- repeated peeking at holdout data.

### Exploratory versus confirmatory separation

AR-2 is exploratory.

Before AR-3, a candidate-specific Confirmatory Hypothesis Contract is frozen.

AR-3 must use an independent or access-controlled confirmatory evidence partition not used to select or tune the candidate.

Repeated exposure to the confirmatory partition contaminates it. Contaminated partitions are retired and versioned as research-visible data.

### Negative controls and empirical null

Negative controls MUST NOT use the rule "non-zero shuffled metric = automatic leakage".

Instead, the harness should construct an empirical null/permutation distribution appropriate to the metric and dependence structure.

Interpretation categories:

- consistent with empirical null → insufficient evidence;
- unexpectedly extreme null-control behavior → leakage/implementation suspicion;
- reproducible candidate advantage over governed baselines and null evidence → eligible for confirmation, not validation;
- ambiguous result → `INVESTIGATE`.

The exact procedure and correction method are candidate/metric-class governed artifacts.

### Multiple testing

Experiment families must record the hypothesis/search count or an equivalent search-space ledger.

Correction method is `TO_BE_SELECTED_BY_PROTOCOL` and may include false-discovery controls or another justified method.

No fixed p-value or correction threshold is mandated by this addendum.

## 8. Feature Research Evidence Model

The default assessment is multidimensional.

### A. Safety Preconditions

Examples:

- point-in-time safety;
- schema/lineage validity;
- reproducibility;
- confirmatory partition integrity;
- no unresolved leakage finding.

Failure makes the experiment invalid or blocked rather than merely lowering a score.

### B. Statistical Evidence

Examples:

- predictive association appropriate to the target;
- uncertainty/confidence interval;
- empirical-null comparison;
- temporal stability;
- confirmatory replication;
- multiple-testing context;
- sample/information sufficiency.

### C. Context / Utility Evidence

Examples:

- regime sensitivity;
- timeframe sensitivity;
- turnover/cost implication;
- liquidity dependence;
- incremental information;
- redundancy;
- parameter fragility;
- cross-asset transfer behavior.

All numeric cutoffs are `TO_BE_CALIBRATED` unless a governed artifact records the empirical basis.

## 9. Incremental information / redundancy

Pairwise linear correlation alone cannot prove redundancy or independence.

Evaluation may combine, as appropriate:

- Pearson/Spearman dependence;
- mutual information or other nonlinear dependence;
- conditional dependence;
- regime-conditioned dependence;
- incremental predictive value;
- ablation;
- nested-baseline comparison.

A candidate should be rejected for redundancy only when governed evidence shows it adds no material information under the relevant protocol, not merely because a single correlation exceeds an arbitrary number.

Formal cross-family independence certification remains P08-H/G6.

## 10. Cross-asset and regime methodology

BTC may be the reference development asset, but Fast Track is BTC-first, not BTC-only.

The sanity universe must be selected ex ante from a governed methodology considering, as applicable:

- data availability and lineage quality;
- liquidity;
- history length;
- venue/instrument comparability;
- market-structure diversity;
- dependency/correlation clusters;
- survivorship/delisting coverage.

Asset choices MUST NOT be changed after seeing candidate performance merely to improve results.

No fixed correlation band, market-cap rank or history threshold is imposed by this addendum.

Cross-asset sanity does not equal production generalization.

Temporal holdout and cross-asset sanity are separate dimensions and may use overlapping calendar periods when the protocol explicitly models shared market dependence; the confirmatory temporal evidence itself must remain protected from exploratory tuning.

## 11. Research Validation Specialist

Identifier:
`research_validation`

Parent:
A4 Quant

Nature:
temporary, bounded specialist-on-demand. It is not A11.

Purpose:
independent screening and confirmatory evaluation of research candidates.

Authority:

- read authorized candidate definitions and research evidence;
- execute the frozen validation protocol;
- issue `REJECT`, `RETAIN_FOR_CONFIRMATION`, `RETAIN_FOR_P17` or `INVESTIGATE`;
- block a result when evidence is contaminated, irreproducible or point-in-time unsafe.

Forbidden:

- changing the candidate to rescue a failing result;
- changing Master Roadmap or gates;
- self-promoting candidate evidence;
- writing execution/risk/production policy;
- interacting with broker/order endpoints;
- creating trading instructions.

Independence controls:

- separate Task Contract;
- bounded write scope;
- builder/evaluator separation;
- frozen candidate configuration before confirmatory access;
- confirmatory dataset access policy;
- immutable decision evidence;
- conflict escalation to A0;
- evidence verification by A10.

RVS may request A2 data review, A4 methodology review, A8 security review or A10 evidence review.

## 12. Evidence contract

Each governed experiment must record enough information to reproduce and audit the claim.

Minimum fields include:

- experiment_id;
- parent task/run IDs;
- code Git SHA;
- config hash;
- runtime/dependency lock/version;
- dataset ID/version/hash;
- data source/provenance references;
- time range and timeframe;
- asset universe and selection-method version;
- event/information/ingestion/feature/decision time semantics;
- feature ID/definition/version/hash;
- parameter set/hash;
- label ID/definition/version/hash;
- regime definition/version/hash;
- exploratory/confirmatory partition identity;
- purge/embargo policy version;
- hypothesis contract ID for confirmatory runs;
- random seed where stochastic operations exist;
- metric definitions/versions;
- empirical-null/negative-control definition;
- multiple-testing ledger/reference;
- result metrics and uncertainty;
- limitation flags;
- decision;
- rejection/retention rationale;
- artifact hashes;
- evaluator identity;
- evidence timestamp.

Hidden notebook state is not valid canonical evidence.

## 13. Build-vs-Buy requirement

Before implementing substantial Fast Track infrastructure, AR-0/AR-1 must create a governed ADR/technology spike.

At minimum evaluate:

- lightweight custom research harness;
- Qlib;
- NautilusTrader;
- LEAN;
- hybrid architecture;
- any later justified candidate.

Official repositories/documentation are authoritative for capabilities and licenses.

Unverified claims are marked `UNVERIFIED`.

The evaluation must separate:

- exploratory/vectorized research needs;
- reproducible experiment tracking needs;
- AR-5 robustness-preview needs;
- P17 event-driven/reality-aware backtest needs;
- future execution-simulation needs.

No tool is selected by this addendum.

## 14. Failure-mode register

Fast Track must detect and mitigate at least these failure classes:

1. hidden lookahead;
2. label leakage;
3. stale/revised data contamination;
4. repeated holdout peeking;
5. data snooping;
6. p-hacking;
7. uncontrolled multiple testing;
8. parameter mining;
9. regime-specific overfit;
10. asset-specific overfit;
11. survivorship bias;
12. cherry-picked universe;
13. misleading composite score;
14. builder/evaluator confirmation bias;
15. irreproducible experiment state;
16. notebook-only evidence;
17. benchmark gaming;
18. false-confidence language;
19. Fast Track becoming a hidden P17;
20. Fast Track becoming a parallel bureaucracy.

Every concrete implementation must map applicable failures to detection, mitigation and escalation.

## 15. Kill / redesign criteria

### Candidate kill

A candidate is rejected when governed evidence establishes a fatal condition such as:

- confirmed leakage or point-in-time invalidity;
- inability to reproduce;
- confirmatory failure under the frozen hypothesis contract;
- empirical behavior indistinguishable from governed null/baseline under the selected protocol;
- no material incremental information under the governed redundancy protocol;
- robustness preview exposes a fatal dependence on a fragile assumption.

Exact thresholds remain protocol-calibrated.

### Experiment-family pause

Pause a family when:

- confirmatory contamination occurs repeatedly;
- the experiment-search ledger is incomplete;
- data provenance cannot be reconstructed;
- metric definitions change without versioning;
- repeated failed controls indicate harness defects.

### Tool-evaluation stop

Stop a tool spike when:

- licensing/security constraints are incompatible with project policy;
- deterministic reproduction cannot be achieved within the intended layer;
- integration burden exceeds the governed scope without compensating benefit.

### Fast Track redesign

Escalate AR-FT for redesign if:

- it materially slows the canonical roadmap without improving early rejection;
- it duplicates P17;
- it repeatedly generates false "validated/profitable" interpretations;
- RVS independence cannot be preserved;
- the Fast Track develops independent production authority;
- governance overhead becomes disproportionate to research value.

## 16. Parallel execution and shared writers

AR-FT may run in parallel only when the Execution Roadmap parallelization rule is satisfied.

Two active tasks must not write the same canonical shared file without explicit coordinated ownership.

For FIN-P08-WJ-001 specifically:

- P08-F currently owns shared reconciliation paths;
- this addendum task is initially restricted to its own contract, addendum and specialist catalog entry;
- `CURRENT-STATE.md`, `TASK-CATALOG.md`, `README.md` and `EXECUTION-ROADMAP.md` reconciliation is deferred until the P08-F lock is released or a coordinated closure task acquires those paths.

## 17. Adoption sequence

1. Merge this addendum package under FIN-P08-WJ-001.
2. Verify Governance and post-merge evidence.
3. After conflicting shared-writer lock release, reconcile Task Catalog / Current State / execution companion as a closure operation.
4. AR-0 may then create its implementation Task Contract.
5. No AR-1+ implementation starts before AR-0 canonicalization.

## 18. Final principle

The Alpha Research Fast Track exists to make NEXUS QUANT faster at rejecting weak ideas, not faster at declaring success.

A retained candidate is not validated.

A promising preview is not a profitable strategy.

Only the canonical roadmap gates can authorize later claims and progression.


## 19. Canonical adoption evidence

Addendum governance package:

- Task: `FIN-P08-WJ-001`
- Linear: `HOS-219`
- PR: `#179` = MERGED
- Final PR head: `28167a9571940c0e13dcf9400d9ef303dcef70ed`
- Merge SHA: `99e27c1f74b5274a5eae29224ef1cd3e36746125`
- PR Governance: `38041755653` = SUCCESS
- PR artifact: `sha256:46ef10cb5af2d96961a3db305f1178dc5e1bf3d7fbebbe53003b38d8c1756a92`
- Post-merge Governance: `38041827701` = SUCCESS
- Post-merge artifact: `sha256:f6a0380bb4cd020e21e1726125020caca187632f04ac6d9c59c41bb05508a905`
- Post-merge Branch Hygiene: `38041827709` = SUCCESS

Deferred shared-state reconciliation is completed by `FIN-P08-WJ-002` / `HOS-220` after the P08-F writer lock was released.

Adoption state after reconciliation:

- Alpha Research Fast Track addendum: CANONICAL_COMPLETE
- AR-0 — Research Governance: READY_NOT_STARTED
- AR-1..AR-5: BLOCKED_UNTIL_AR0_CANONICAL
- P08-G remains READY_NOT_STARTED
- Master Roadmap v2.0 remains FROZEN and unchanged
- G6/G7/G8/G9 authority remains canonical and unchanged

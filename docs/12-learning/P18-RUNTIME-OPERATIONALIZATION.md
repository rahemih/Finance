# P18 Runtime Operationalization — FIN-P18-WI-001-R01

State: CANONICAL_COMPLETE after governed merge

## Objective

Convert the P18-I deterministic operating contract into a recurring DEMO-only reference runtime without granting execution or Live-promotion authority.

## Runtime

The operational path is `packages.learning.runtime` with `scripts/runtime/p18_demo_worker.py`.

It provides:
- repeated execution of all nine P18 learning stages;
- atomic JSON checkpoint persistence after every completed stage;
- deterministic restart/resume from the last persisted stage;
- bounded retry/backoff and SAFE_HOLD on repeated failure;
- JSONL telemetry and alerts;
- market-watermark and system-state interfaces;
- content-addressed, cycle-specific stage evidence;
- multi-cycle operation with no broker/exchange routing.

## Evidence bundle

`scripts/ci/p18_reference_stage_bundle.py` builds the runtime stage bundle from:
- the checked-in non-fixture BTC-USD public-market reference dataset;
- empirical P17 G9 reference evidence;
- authoritative same-run P18 canonical lineage evidence derived from P14/P15/P16/P17.

The public-market reference was revalidated during this repair; Sep 28 was added and the Sep 29 row was corrected to match the cited Yahoo Finance historical table.

## Persistence across scheduled runs

`.github/workflows/p18-demo-learning-runtime.yml` runs hourly.

The workflow:
- restores the latest prior runtime-state cache;
- regenerates canonical upstream evidence;
- runs three additional DEMO learning cycles;
- atomically updates the checkpoint;
- preserves checkpoint/telemetry/alerts in a new cache generation;
- uploads a 30-day runtime evidence artifact.

The workflow is read-only to repository contents, uses no secrets and never routes orders.

## Validation

Governance requires:
- direct runtime unit tests;
- restart/resume proof;
- stale-data WAIT behavior;
- repeated-failure SAFE_HOLD behavior;
- unique cycle-specific stage chains;
- 20 complete cycles in a bounded soak;
- a second independent 20-cycle soak with byte-identical report/checkpoint/telemetry output;
- workflow supply-chain security.

## Boundary

This is a continuously scheduled reference DEMO runtime over governed canonical/reference evidence. It is not Live Trading, broker execution, a profitability guarantee, or P19 Shadow/Digital Twin work.

Automatic Live promotion = false.
LIVE_TRADING = DISABLED.
AUTO_TRADING = DISABLED.
P19 = NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED.


## R03 authoritative runtime execution — FIN-P18-WI-001-R03

R03 supersedes the R01 evidence-bundle executor as the authoritative scheduled runtime.

The canonical stage executor now invokes the real P18 components for every cycle:
`Observe/Analyze -> Demo/Paper -> Outcome -> Journal -> Dataset -> Experiment -> Controlled Retraining -> Champion/Challenger + Drift -> Promotion Governance`.

The previous `BundleStageExecutor` remains available only for isolated self-tests; it is not the authoritative scheduled path.

Each stage writes a content-addressed JSON artifact. Before a later stage resumes, the runtime reloads the exact persisted JSON representation and verifies that its identity matches the checkpointed evidence. Scheduled state uses the versioned `canonical-v2` cache namespace, preventing legacy bundle-state reuse.

The scheduled workflow also runs as a PR fast preflight. PR fast preflight `39039915544` and post-merge runtime `39040128177` both succeeded. The post-merge runtime artifact is `12103478518` with digest `sha256:54cd6dd7d776b85d8508894aa5844c0d3adcaf25ed25798f0fc09b9c89c57f32`.

Governance `39039915556` and `39040128212` each passed two deterministic 20-cycle canonical end-to-end soaks.

P19 remains NOT_STARTED. Live/Auto remain disabled.

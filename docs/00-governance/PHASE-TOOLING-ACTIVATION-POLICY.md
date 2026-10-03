# NEXUS QUANT — Phase Tooling Activation Policy

STATE = GOVERNED_POLICY  
TASK = `FIN-P01-WM-001`  
LINEAR = `HOS-118`

## 1. Purpose

Registered tools and capabilities must be reconsidered automatically at the roadmap phase that owns them. The Owner does not need to remember individual tool names.

This policy does **not** auto-install every candidate. It auto-triggers evaluation.

## 2. Mandatory phase-start procedure

At the start of every roadmap phase, A0 Governance / Orchestrator must:

1. read `PROJECT-CAPABILITY-TOOLING-MASTER-REGISTRY.md` and its JSON form;
2. select capabilities whose owner phase includes the current phase;
3. read each linked specialist registry;
4. revalidate current version, upstream health, license, CVEs/security posture, cost and project fit;
5. detect overlapping tools;
6. create a `Tooling Plan` section in the phase Task Contract;
7. classify each applicable entry as:
   - `SELECT`
   - `PILOT`
   - `DEFER`
   - `REJECT`
   - `NOT_APPLICABLE`
8. install/configure only entries that are explicitly selected and whose gates permit the action;
9. capture evidence and rollback/exit strategy;
10. update the Master Registry if a material decision changes future phases.

## 3. Activation modes

### ACTIVE_NOW
Use immediately within existing scope.

### BASELINE_STANDARD
Design and contracts must conform to the standard even when no package installation is needed.

### ADOPT_CANDIDATE
Must be explicitly evaluated at the owner phase. Selection requires evidence.

### USE_CANDIDATE
Evaluate only for the bounded need described in the registry.

### ALTERNATIVE
Compare only when the preferred candidate is unsuitable or a benchmark requires comparison.

### CONDITIONAL
Do not evaluate unless the triggering architecture condition exists.

### LICENSE_REVIEW
No production adoption until exact current terms are verified.

### HUMAN_GATE
Stop at the approval point and request explicit authorized human action.

### DEFERRED
Do not activate before the owning phase.

## 4. Installation gate

A runtime tool may be installed/configured only if:

- phase/task scope requires it;
- the active Task Contract lists it;
- upstream version/health is current enough;
- license/legal use is acceptable;
- dependency/SBOM/CVE review is complete at the required risk level;
- secrets/access model is defined;
- deployment/backup/rollback is defined;
- observability is defined;
- test/benchmark evidence supports the selection;
- overlapping tools are not being installed without justification.

## 5. Upgrade gate

Selected tooling must not float silently to latest.

Upgrades require:
- version diff/release-note review;
- compatibility tests;
- security/license re-check when material;
- rollback plan;
- evidence in the governing task/PR.

## 6. Retirement gate

A tool may be retired when:
- unused;
- superseded;
- license/risk becomes unacceptable;
- operational burden exceeds value;
- architecture changes.

Retirement must include data/config migration and removal evidence.

## 7. Tooling Plan template

Every implementation phase Task Contract should contain:

```text
Applicable registered capabilities:
Selected:
Pilots:
Deferred:
Rejected:
Alternatives considered:
Exact versions:
License findings:
Security/SBOM findings:
Secrets/access:
Benchmark evidence:
Operational cost:
Observability:
Rollback/exit:
Human gates:
```

## 8. Automatic re-evaluation map

- P02: architecture, API/event contracts, OpenTelemetry, IaC candidate, runtime boundaries, agent/automation architecture.
- P03: policy-as-code, IAM/secrets/KMS, supply-chain security design, audit integrity.
- P04: exact packages/versions, CI/CD, SBOM, signing, feature flags, config, artifact registry.
- P05/P06: data quality, lineage, Arrow/Parquet, replay, orchestration, freshness/backfill.
- P14/P17/P18: MLflow, feature store decision, evaluation harness, model registry, training/retraining workflows.
- P22: observability backend, durable operations, incidents, load/failure testing, runbooks, FinOps.
- P23: frontend stack finalization, accessibility, feature flags, E2E/visual tests, workflow UX.
- P24: chaos/recovery/replay/load/security final validation.

## 9. Human Gate boundaries

Automatic phase activation may prepare evidence but may not:
- purchase or accept paid/commercial terms for the Owner;
- create/fund real broker or exchange accounts;
- grant withdrawal permissions;
- expose production secrets;
- raise risk ceilings;
- enable Live Trading;
- enable unrestricted Auto Trading.

## 10. Source-of-truth rule

Tool availability, a plugin connection, a GitHub star count, or a prior recommendation is never a production architecture decision.

Production selection exists only when canonical Task/ADR/PR evidence says so.

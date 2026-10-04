# NEXUS QUANT — Build Readiness Checklist

STATE = GOVERNED_CURRENT_STATE_COMPANION  
TASK = `FIN-P01-WM-001`  
EFFECTIVE_DATE = 2026-10-03

## 1. Purpose

This checklist answers one question:

> Are we ready to begin implementation with the right capabilities identified, governed and phase-owned?

It is not a substitute for roadmap gates. A green tooling checklist does not bypass unfinished P01 work.

## 2. Tooling readiness

- [x] Canonical GitHub/Linear governance established.
- [x] Plugin / connector / skill matrix exists.
- [x] Open-source finance/quant repository registry exists.
- [x] Frontend UI/UX repository registry exists.
- [x] Frontend excellence baseline exists.
- [x] Agent framework / ready-agent registry exists.
- [x] Agent governance / authority baseline exists.
- [x] Automation & orchestration registry exists.
- [x] Automation governance baseline exists.
- [x] Master capability/tooling registry exists.
- [x] Machine-readable tooling registry exists.
- [x] Phase Tooling Activation Policy exists.
- [x] Human Gate boundaries for tooling activation are defined.
- [x] Anti-sprawl / overlapping-tool rules are defined.

TOOLING_READINESS = PASS

## 3. Architecture-readiness inputs

- [x] API contract standards identified: OpenAPI / JSON Schema.
- [x] Event contract standard identified: AsyncAPI candidate.
- [x] Observability standard identified: OpenTelemetry candidate.
- [x] Policy-as-code candidate identified: OPA.
- [x] IaC candidate identified: OpenTofu.
- [x] Secret-management capability identified.
- [x] Environment/configuration policy requirement identified.
- [x] Time synchronization/timestamp discipline identified.
- [x] Feature-flag standard candidate identified: OpenFeature.
- [ ] Final architecture selections completed.
- [ ] Exact runtime versions pinned.

ARCHITECTURE_SELECTION_READINESS = INPUTS_READY / SELECTION_DEFERRED_TO_P02_P04

## 4. Data-readiness inputs

- [x] Data-provider inventory exists.
- [x] Broker/exchange inventory exists.
- [x] Data quality capability identified.
- [x] Lineage candidate identified: OpenLineage.
- [x] Arrow/Parquet candidates identified.
- [x] Deterministic replay is registered as project-core capability.
- [x] Synthetic/test-data requirement identified.
- [ ] P01 provider baseline finalized.
- [ ] P05/P06 canonical ingestion/storage architecture implemented.

DATA_TOOLING_READINESS = INPUTS_READY / IMPLEMENTATION_DEFERRED

## 5. Quant / ML readiness inputs

- [x] Finance/quant OSS registry exists.
- [x] Experiment tracking candidate identified: MLflow.
- [x] Model registry capability identified.
- [x] Feature-store candidate identified: Feast.
- [x] Evaluation/red-team candidates identified.
- [x] Model/agent provenance requirements identified.
- [ ] Model lifecycle architecture selected.
- [ ] Training/retraining/promotion pipelines implemented.

ML_TOOLING_READINESS = INPUTS_READY / IMPLEMENTATION_DEFERRED

## 6. Security / supply-chain readiness inputs

- [x] Secret Protection / Push Protection active.
- [x] Security-analysis tooling available.
- [x] SBOM candidate identified: Syft + CycloneDX.
- [x] Signing candidate identified: Cosign.
- [x] Build provenance standard identified: SLSA-class.
- [x] Policy-as-code candidate identified.
- [x] Security tooling registry exists.
- [x] Primary SAST candidate identified: GitHub CodeQL.
- [x] Broad vulnerability/misconfiguration candidate identified: Trivy.
- [x] Custom SAST candidate identified: Semgrep.
- [x] DAST/API candidate identified: OWASP ZAP.
- [x] Runtime security candidate identified: Falco (conditional).
- [x] Independent SBOM vulnerability scanner identified: Grype.
- [x] Least-privilege / Human Gate model defined.
- [ ] P03 security architecture completed.
- [ ] P04 supply-chain CI gates implemented.

SECURITY_TOOLING_READINESS = INPUTS_READY / IMPLEMENTATION_DEFERRED

## 7. Reliability / operations readiness inputs

- [x] Durable workflow candidate identified: Temporal.
- [x] Data/ML orchestration candidate identified: Dagster.
- [x] Event/ops automation candidate identified: Kestra.
- [x] External integration automation candidate identified: n8n.
- [x] Load-test capability identified: k6-class.
- [x] Fault-injection / chaos capability identified.
- [x] Runbook / incident / recovery requirements identified.
- [x] FinOps/cost telemetry requirement identified.
- [ ] P22 operational architecture implemented.
- [ ] P24 chaos/recovery/load acceptance complete.

OPERATIONS_TOOLING_READINESS = INPUTS_READY / IMPLEMENTATION_DEFERRED

## 8. Frontend / UX readiness inputs

- [x] Frontend stack candidates registered.
- [x] Design system / tokens / Figma baseline defined.
- [x] Accessibility baseline defined.
- [x] Visual regression / E2E / performance requirements defined.
- [x] RTL/LTR financial UX rules defined.
- [ ] P23 production frontend implementation completed.

FRONTEND_TOOLING_READINESS = INPUTS_READY / IMPLEMENTATION_DEFERRED

## 9. Current roadmap blockers to actual build start

The project is **not yet authorized to skip directly into broad runtime implementation**.

Current roadmap still requires P01 completion, including:
- P01-E — Cost / Licensing / Data Rights;
- subsequent P01 provider strategy/baseline workstreams required by the frozen roadmap;
- any required Human Gates.

Therefore:

```text
TOOLING_ARSENAL_READY = PASS
BROAD_BUILD_START_GATE = NOT_YET
REASON = ROADMAP P01 NOT YET CANONICALLY COMPLETE
```

## 10. Build-start rule

When the roadmap reaches P02:

1. run Fresh Live Guard;
2. read the Master Tooling Registry;
3. generate the P02 Tooling Plan automatically;
4. revalidate applicable candidates;
5. create ADRs/Task Contracts;
6. select the minimum justified stack;
7. install only selected/approved dependencies;
8. establish P03/P04 security/supply-chain gates before sensitive runtime expansion.

## 11. Readiness principle

The goal is not to own the largest toolbox.

The goal is to ensure that when a capability is needed:
- a vetted candidate is already known;
- its phase owner is known;
- its security/license gate is known;
- its alternatives are known;
- and its adoption path is governed.

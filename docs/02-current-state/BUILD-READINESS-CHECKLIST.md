# NEXUS QUANT — Build Readiness Checklist

STATE = GOVERNED_CURRENT_STATE_COMPANION  
TASK = `FIN-P01-WM-001`  
EFFECTIVE_DATE = 2026-10-04

## 1. Purpose

This checklist answers one question:

> Are we ready to begin implementation with the right capabilities identified, governed and phase-owned?

It is not a substitute for roadmap gates. A green tooling checklist does not bypass phase dependencies, safety gates or explicit Owner authorization.

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
- [x] Final P02 architecture selections completed and frozen at G2.
- [x] Exact P04 runtime/package-manager versions pinned.

ARCHITECTURE_SELECTION_READINESS = PASS / P02_G2 + P04_B

## 4. Data-readiness inputs

- [x] Data-provider inventory exists.
- [x] Broker/exchange inventory exists.
- [x] Data quality capability identified.
- [x] Lineage candidate identified: OpenLineage.
- [x] Arrow/Parquet candidates identified.
- [x] Deterministic replay is registered as project-core capability.
- [x] Synthetic/test-data requirement identified.
- [x] P01 provider baseline finalized.
- [ ] P05/P06 canonical real-time/historical ingestion and storage implementation completed.

DATA_TOOLING_READINESS = FOUNDATION_READY / P05_P06_RUNTIME_IMPLEMENTATION_DEFERRED

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
- [x] P03 security architecture completed / G3_SECURITY_BASELINE PASS.
- [x] P04 supply-chain CI gates implemented and enforced in required `governance`.

SECURITY_TOOLING_READINESS = PASS_FOR_ENGINEERING_FOUNDATION

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

## 9. Current roadmap boundary

P00 through P04 are canonically complete at the current baseline.

Engineering Foundation readiness is proven, but this does **not** authorize skipping the P05 phase boundary or later safety gates.

Therefore:

```text
TOOLING_ARSENAL_READY = PASS
ENGINEERING_FOUNDATION_READY = PASS
P04 = CANONICAL_COMPLETE
P05 = NOT_STARTED_PENDING_OWNER_AUTHORIZATION
LIVE_TRADING = DISABLED
AUTO_TRADING = DISABLED
```

## 10. Next build-start rule

Before entering P05:

1. obtain explicit Owner authorization for the phase boundary;
2. run Fresh Live Guard against canonical `main`, Linear and active locks;
3. verify `P04_ENGINEERING_FOUNDATION_EXIT=PASS`;
4. read the Master Tooling Registry and P05 tooling map;
5. create the first P05 Task Contract and lock;
6. select only the minimum provider/runtime dependencies justified for that workstream;
7. keep provider credentials, CANARY, LIVE and AUTO_TRADING disabled unless their later governed gates authorize them;
8. preserve P03/P04 security, supply-chain and reproducibility checks in required CI.

## 11. Readiness principle

The goal is not to own the largest toolbox.

The goal is to ensure that when a capability is needed:
- a vetted candidate is already known;
- its phase owner is known;
- its security/license gate is known;
- its alternatives are known;
- and its adoption path is governed.

# Finance / NEXUS QUANT — Project Capability & Tooling Master Registry

STATE = GOVERNED_MASTER_REGISTRY  
TASK = `FIN-P01-WM-001`  
LINEAR = `HOS-118`  
EFFECTIVE_DATE = 2026-10-03  
PRODUCTION_INSTALLATIONS = NOT_AUTHORIZED_BY_THIS_REGISTRY

## 1. Purpose

This is the central index for project capabilities and tooling. It does not replace specialist registries; it links them and defines when each capability must be evaluated, selected, installed, configured or kept deferred.

The governing rule is:

```text
Useful capability
  -> registered now
  -> revalidated at owning roadmap phase
  -> benchmark/security/license review
  -> selected only if justified
  -> installed/configured only after governance permits it
  -> continuously observed and replaceable
```

## 2. Existing canonical registries

| Domain | Canonical source |
|---|---|
| ChatGPT plugins/connectors/skills | `docs/09-agents/TOOLCHAIN-MATRIX.md` |
| Open-source finance/quant repositories | `docs/03-research/OPEN-SOURCE-REPOSITORY-DEPENDENCY-REGISTRY.md` |
| Frontend UI/UX | `docs/03-research/FRONTEND-UI-UX-REPOSITORY-REGISTRY.md` |
| Frontend quality baseline | `docs/03-research/FRONTEND-EXCELLENCE-BASELINE.md` |
| Agents/frameworks/interoperability | `docs/03-research/AGENT-FRAMEWORK-READY-AGENT-REGISTRY.md` |
| Agent authority/governance | `docs/09-agents/AGENT-GOVERNANCE-INTEGRATION.md` |
| Automation/orchestration | `docs/03-research/AUTOMATION-ORCHESTRATION-REGISTRY.md` |
| Automation governance | `docs/00-governance/AUTOMATION-GOVERNANCE.md` |

## 3. Activation states

- `ACTIVE_NOW`: already approved and actively used for project work.
- `BASELINE_STANDARD`: specification/protocol to design against; may not require runtime installation.
- `ADOPT_CANDIDATE`: preferred candidate requiring later phase validation.
- `USE_CANDIDATE`: bounded-use candidate.
- `ALTERNATIVE`: viable fallback/alternative; not installed in parallel by default.
- `CONDITIONAL`: only if architecture/use-case requires it.
- `LICENSE_REVIEW`: terms must be revalidated before adoption.
- `HUMAN_GATE`: cannot be activated without explicit Owner/Human approval.
- `DEFERRED`: intentionally not active yet.

## 4. Master capability matrix

### Governance / project control

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Repository source of truth | GitHub | ACTIVE_NOW | P00+ | always |
| Project execution mirror | Linear | ACTIVE_NOW | P00+ | always |
| Task contracts / locks / evidence | repository-native governance | ACTIVE_NOW | P00+ | always |
| Policy-as-code | Open Policy Agent (OPA) | ADOPT_CANDIDATE | P03/P04 | evaluate -> benchmark -> ADR -> install |
| Architecture decisions | ADR | BASELINE_STANDARD | P02+ | required for major decisions |
| Architecture diagrams | C4-style model + Figma/Mermaid/diagram tooling | BASELINE_STANDARD | P02+ | create/update with architecture changes |

### Contracts / APIs / events

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| HTTP/API contract | OpenAPI | BASELINE_STANDARD | P02/P04 | design from P02; tooling P04 |
| Async/event contract | AsyncAPI | BASELINE_STANDARD | P02/P05 | design from P02; enforce when event bus exists |
| Validation/schema | JSON Schema + typed contracts | BASELINE_STANDARD | P02/P04 | mandatory for machine boundaries |
| Contract testing | schema/OpenAPI/AsyncAPI contract tests | BASELINE_STANDARD | P04+ | CI gate when services appear |
| Schema compatibility | versioned compatibility rules | BASELINE_STANDARD | P04/P05 | CI/event gate |

### Observability / evidence

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Telemetry standard | OpenTelemetry | ADOPT_CANDIDATE / STANDARD | P02/P22 | instrument early; backend selected later |
| Metrics/logs/traces backend | Grafana/Sentry/PostHog/managed equivalents | CONDITIONAL | P22 | select by operational needs |
| Immutable audit/evidence | repository + append-only/tamper-evident store later | BASELINE_STANDARD | P03/P22 | architecture + implementation |
| Agent tracing/evals | OpenTelemetry + agent trace platform candidate | CONDITIONAL | P02-F/P22 | after agent runtime selection |

### Infrastructure / configuration / secrets

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Infrastructure-as-Code | OpenTofu | ADOPT_CANDIDATE | P02/P04 | select after hosting topology |
| Container image/package registry | GitHub Packages / GHCR-class | USE_CANDIDATE | P04 | when build artifacts exist |
| Secrets management | approved cloud KMS/secret manager; Vault candidate | ADOPT/USE_CANDIDATE + LICENSE_REVIEW | P03/P04 | select after hosting/security architecture |
| Typed configuration | schema-validated config | BASELINE_STANDARD | P02/P04 | required before production environments |
| Environment separation | dev/test/staging/prod policy | BASELINE_STANDARD | P03/P04 | mandatory before sensitive runtime |
| Time synchronization | NTP/chrony-class + timestamp contracts | BASELINE_STANDARD | P02/P05 | mandatory for market/event correctness |

### Data engineering

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Data quality | Great Expectations/Soda-class framework | USE_CANDIDATE | P05/P06 | benchmark against project checks |
| Data lineage | OpenLineage | ADOPT_CANDIDATE | P05/P06 | adopt if pipeline graph requires standardized lineage |
| Columnar in-memory format | Apache Arrow | ADOPT_CANDIDATE | P06 | benchmark and adopt where useful |
| Analytical storage format | Apache Parquet | ADOPT_CANDIDATE | P06 | default candidate for historical analytical datasets |
| Dataset version/provenance | governed metadata + object store/versioning | BASELINE_STANDARD | P06 | mandatory |
| Replay | deterministic event/market replay engine | PROJECT_CORE_CAPABILITY | P06+ | build after canonical event/data contracts |
| Synthetic/test data | deterministic fixtures/generators | BASELINE_STANDARD | P04/P06 | build with contracts |
| Data catalog | metadata/catalog capability | CONDITIONAL | P06/P22 | add if scale/team complexity justifies |

### Quant / ML / AI lifecycle

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Experiment tracking | MLflow | ADOPT_CANDIDATE | P14/P17 | benchmark + privacy/storage review |
| Model registry | MLflow registry or governed equivalent | ADOPT_CANDIDATE | P17/P18 | when model promotion exists |
| Feature store | Feast | USE_CANDIDATE | P14/P17 | only if training/serving consistency needs dedicated store |
| Evaluation harness | project benchmark suites + Inspect AI/Promptfoo where relevant | ADOPT/USE_CANDIDATE | P14/P17/P18 | phase-specific |
| Model/agent provenance | version + dataset + code SHA + params + evidence | BASELINE_STANDARD | P14+ | mandatory |
| Agent orchestration | specialist Agent Registry | DEFERRED_TO_P02_F | P02-F/P04 | automatic re-evaluation at phase |
| LLM/agent interoperability | MCP / A2A | CONDITIONAL | P02-F/P04 | only if runtime boundaries justify |

### Automation / workflow

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| CI/governance automation | GitHub Actions | ACTIVE_NOW | P00+ | always |
| Critical durable workflows | Temporal | ADOPT_CANDIDATE | P02/P04/P22 | revalidate at architecture |
| Data/ML orchestration | Dagster | ADOPT_CANDIDATE | P05/P06/P17 | revalidate at owning phase |
| Event/schedule/ops automation | Kestra | USE_CANDIDATE | P04/P22 | only if distinct need remains |
| External integrations | n8n | USE_CANDIDATE + LICENSE_REVIEW | P22/P23 | bounded use only |
| Python pipeline alternative | Prefect | ALTERNATIVE | P05/P06 | compare against Dagster |
| Batch scheduler reference | Airflow | ALTERNATIVE/REFERENCE | P05/P06 | only if requirements fit |
| TS background jobs | Trigger.dev | SPECIALIST_CANDIDATE | P04/P23 | if TS workload justifies |
| Internal ops scripts/workflows | Windmill | SPECIALIST + LICENSE_REVIEW | P22 | conditional |

### Security / software supply chain

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Secret scanning | GitHub Secret Protection | ACTIVE_NOW | P00+ | always |
| Dependency/SCA scanning | GitHub/native + selected scanner | ADOPT_CANDIDATE | P03/P04 | CI gate |
| SBOM generation | Syft + CycloneDX format/tools | ADOPT_CANDIDATE | P03/P04 | build/release gate |
| Artifact signing | Sigstore/Cosign | ADOPT_CANDIDATE | P04 | release gate |
| Build provenance | SLSA-class provenance | BASELINE_STANDARD | P04 | CI/release policy |
| SAST/security analysis | Codex Security + CI scanner candidates | ACTIVE/CANDIDATE | P03/P04 | governed |
| DAST/app security | later selected web/API security tooling | CONDITIONAL | P03/P24 | before production gates |
| Policy enforcement | OPA + repository governance | ADOPT_CANDIDATE | P03/P04 | if centralized policy improves safety |

### Reliability / testing / validation

| Capability | Tool / baseline | State | Owner phase | Activation |
|---|---|---|---|---|
| Unit/integration tests | native framework tooling | BASELINE_STANDARD | P04+ | mandatory |
| Contract tests | OpenAPI/AsyncAPI/schema harness | BASELINE_STANDARD | P04+ | mandatory |
| E2E | browser/API workflow tooling | BASELINE_STANDARD | P23/P24 | mandatory for critical paths |
| Load testing | k6-class | USE_CANDIDATE + LICENSE_REVIEW | P22/P24 | benchmark before production |
| Fault injection | Toxiproxy-class / project failure harness | USE_CANDIDATE | P22/P24 | preferred before K8s-specific chaos |
| Kubernetes chaos | Chaos Mesh | CONDITIONAL | P22/P24 | only if Kubernetes is actually selected |
| Visual regression | frontend snapshot/visual tooling | BASELINE_STANDARD | P23 | mandatory critical UI |
| Replay regression | deterministic replay corpus | PROJECT_CORE_CAPABILITY | P06/P24 | mandatory for market/execution correctness |

### Frontend / product

See:
- `FRONTEND-UI-UX-REPOSITORY-REGISTRY.md`
- `FRONTEND-EXCELLENCE-BASELINE.md`

Core direction remains Next.js/React/TypeScript + product-owned design system with candidate layers such as shadcn/ui, Lightweight Charts, TanStack and Better Auth subject to later selection.

### Plugins / skills / connected development tools

See:
- `docs/09-agents/TOOLCHAIN-MATRIX.md`

Installed/available ChatGPT-side tooling assists research, engineering, design, project management and evidence. Installation in ChatGPT never implies production dependency selection.

## 5. External tool metadata verified for this baseline

Verified through current upstream repository metadata on 2026-10-03:

- OPA — Apache-2.0, active.
- OpenTofu — MPL-2.0, active.
- Vault — active; GitHub license metadata not sufficient for adoption, exact current terms require review.
- OpenTelemetry Specification — Apache-2.0, active.
- OpenLineage — Apache-2.0, active.
- Feast — Apache-2.0, active.
- MLflow — Apache-2.0, active.
- OpenFeature Specification — Apache-2.0, active.
- Syft — Apache-2.0, active.
- Cosign — Apache-2.0, active.
- k6 — AGPL-3.0; license/use-mode review required before production adoption.
- Chaos Mesh — Apache-2.0; conditional on Kubernetes.
- Apache Arrow — Apache-2.0.
- Apache Parquet format — Apache-2.0.
- OpenAPI Specification — Apache-2.0.
- AsyncAPI Specification — Apache-2.0.
- CycloneDX CLI — Apache-2.0.

## 6. Automatic phase re-evaluation rule

At the start of every roadmap phase, A0 must:

1. read this Master Registry;
2. select entries whose `owner_phase` includes the phase;
3. re-check upstream health, version, license, security and project fit;
4. compare overlapping candidates;
5. create/extend the phase Task Contract with only justified tools;
6. install/configure only after the phase's governance gates permit it;
7. record rejected/deferred candidates so they are not repeatedly reconsidered without new evidence.

The Owner does not need to remind the project about registered tools.

## 7. Anti-sprawl rule

The project must not install tools simply to "have them ready."

For overlapping capabilities, default to one selected implementation plus a documented fallback.

Examples:
- Dagster vs Prefect vs Airflow: one primary unless distinct workloads prove otherwise.
- Temporal vs Kestra vs Trigger.dev: select by workflow class; avoid redundant durable runtimes.
- Neon vs Supabase: production architecture selects, plugin availability does not.
- Phoenix vs Langfuse vs other agent observability: one backend by measured need.

## 8. Human-gated areas

No registry/automation may autonomously:
- accept legal/commercial terms on Owner's behalf;
- purchase a paid plan;
- create or fund a broker/exchange account;
- enable withdrawal-capable credentials;
- raise production risk ceilings;
- enable Live Trading;
- enable unrestricted Auto Trading;
- bypass A5 Risk or A8 Security vetoes.

## 9. Definition of "tool-ready"

A capability is tool-ready only when:
- requirement is documented;
- candidate exists;
- owner phase is known;
- evaluation criteria exist;
- security/license gate is known;
- fallback/exit path exists;
- no unresolved prerequisite prevents evaluation.

Tool-ready does **not** mean installed.

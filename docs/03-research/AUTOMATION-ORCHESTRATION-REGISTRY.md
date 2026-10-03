# Finance / NEXUS QUANT — Automation & Orchestration Registry

STATE = GOVERNED_RESEARCH_REGISTRY  
TASK = `FIN-P01-WO-001`  
LINEAR = `HOS-116`  
EFFECTIVE_DATE = 2026-10-03  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED  
RUNTIME_INSTALLATION = NOT_AUTHORIZED

## 1. Purpose

This registry records automation/orchestration systems that may improve NEXUS QUANT while avoiding premature installation and overlapping orchestrator sprawl.

GitHub Actions remains the existing canonical CI/governance automation layer.

## 2. Classification

- `ADOPT_CANDIDATE`: strong candidate for a core automation role, subject to later architecture/dependency gates.
- `USE_CANDIDATE`: candidate for a bounded subsystem.
- `ALTERNATIVE_CANDIDATE`: viable alternative; do not install in parallel by default.
- `SPECIALIST_CANDIDATE`: useful for a narrow workflow class.
- `REFERENCE`: architecture/reference only unless promoted later.
- `LICENSE_REVIEW_REQUIRED`: exact production terms must be verified before use.
- `EXISTING_CANONICAL`: already used by repository governance.

## 3. Registry

Observed GitHub metadata: 2026-10-03.

| Project | Intended role | Upstream signal | License signal | Classification | NEXUS use |
|---|---|---|---|---|---|
| GitHub Actions | CI, governance, repository automation | existing in repo | platform service | EXISTING_CANONICAL | CI, Governance Verify, Branch Hygiene |
| `temporalio/temporal` | durable stateful workflows | ~23.4k stars; push 2026-10-03 | MIT | ADOPT_CANDIDATE | critical long-running workflows, retries, recovery, approvals |
| `dagster-io/dagster` | data/ML asset orchestration | ~16.2k stars; push 2026-10-02 | Apache-2.0 | ADOPT_CANDIDATE | datasets, features, backfills, lineage, model/data pipelines |
| `kestra-io/kestra` | event/schedule orchestration | ~28.9k stars; push 2026-10-03 | Apache-2.0 | USE_CANDIDATE | event-driven jobs, scheduled operations, infra workflows |
| `n8n-io/n8n` | external integration automation | ~206k stars; push 2026-10-03 | GitHub metadata NOASSERTION | USE_CANDIDATE + LICENSE_REVIEW_REQUIRED | notifications, webhooks, SaaS integration only unless later approved |
| `PrefectHQ/prefect` | Python workflow/data orchestration | ~24k stars; push 2026-10-02 | Apache-2.0 | ALTERNATIVE_CANDIDATE | alternative to Dagster for Python-centric pipelines |
| `apache/airflow` | batch scheduling/orchestration | ~47k stars; push 2026-10-03 | Apache-2.0 | REFERENCE / ALTERNATIVE_CANDIDATE | mature batch scheduling reference |
| `triggerdotdev/trigger.dev` | durable TypeScript background/AI jobs | ~16.5k stars; push 2026-10-02 | Apache-2.0 | SPECIALIST_CANDIDATE | TS-heavy background jobs if Temporal/Kestra do not cover the need |
| `windmill-labs/windmill` | scripts/workflows/internal tools | ~18.1k stars; push 2026-10-03 | GitHub metadata NOASSERTION | SPECIALIST_CANDIDATE + LICENSE_REVIEW_REQUIRED | internal operations/scripts/UI workflows |

## 4. Preferred direction

Current research preference, not a production decision:

```text
GitHub Actions
  -> repository CI / governance

Temporal
  -> critical durable business/workflow orchestration

Dagster
  -> data / quant / ML asset pipelines

Kestra
  -> event/schedule/operations automation where a distinct need remains

n8n
  -> optional external integrations and notifications after license review
```

Prefect, Airflow, Trigger.dev and Windmill remain alternatives/specialists.

## 5. Automation domains

Candidates may support:
- market/reference data ingestion;
- data-quality checks;
- stale/gap/duplicate detection;
- provider health and fallback coordination;
- feature/dataset generation;
- backtests and research pipelines;
- walk-forward / Monte Carlo jobs;
- model training/evaluation/retraining workflows;
- daily/weekly/monthly reports;
- cache warming and scheduled snapshots;
- alert delivery;
- incident creation and recovery workflows;
- reconciliation;
- backups/retention/cleanup;
- dependency/security scans;
- agent workflow scheduling and bounded Human Gate workflows.

## 6. Selection rules

Do not install multiple overlapping orchestrators merely because they are useful.

A candidate may be adopted only when:
- a concrete workflow class needs it;
- exact version/license is reviewed;
- SBOM/CVE/transitive review passes;
- deployment/backup/upgrade path is known;
- retry/idempotency semantics are tested;
- observability and audit integration are defined;
- failure/recovery drills pass;
- operating cost is acceptable;
- exit/replacement path is documented.

## 7. Roadmap ownership

- P02: automation boundaries, runtime ownership and architecture decisions.
- P04: CI/CD, exact dependency/runtime selection and supply-chain controls.
- P05/P06: ingestion, data-quality, backfill and freshness workflows.
- P14/P17/P18: model evaluation, training, retraining and promotion pipelines.
- P22: operations, observability, incident, recovery and resilience automation.
- P23: human-facing workflow/status UX where needed.
- P24: final chaos/recovery/rollback validation.

## 8. Explicit non-decisions

This registry does not install any automation engine, create credentials, select production hosting, enable production trading automation, or override any Owner/Human Gate.

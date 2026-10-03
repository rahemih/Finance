# NEXUS QUANT — Automation Governance Baseline

STATE = GOVERNED_COMPANION  
TASK = `FIN-P01-WO-001`  
LINEAR = `HOS-116`

## 1. Core principle

Automation executes governed work; it does not create authority.

Every automated workflow must operate inside:
`Roadmap ∩ Task Contract ∩ Risk/Security Policy ∩ Human/Owner Gates`.

## 2. Workflow contract minimum

Each production workflow must define:
- workflow ID and owner;
- trigger;
- inputs/outputs;
- dependencies;
- data freshness requirements;
- read/write scope;
- idempotency key;
- retry policy;
- timeout;
- concurrency limit;
- checkpoint/recovery behavior;
- rollback/compensation;
- observability;
- evidence/audit requirements;
- failure state;
- escalation path;
- Human Gate conditions.

## 3. Trigger classes

Supported classes:
- schedule;
- event;
- webhook;
- repository/CI event;
- data-arrival event;
- provider-health event;
- manual governed dispatch;
- bounded agent request.

Triggers do not broaden permissions.

## 4. Reliability rules

- retries are bounded and observable;
- non-idempotent actions require explicit deduplication/compensation;
- long-running workflows need durable checkpoints where correctness requires them;
- poison messages/jobs must move to a dead-letter or quarantine state;
- repeated failure triggers a circuit breaker;
- backfills must be explicit and distinguishable from live runs;
- recovery must not silently fabricate missing outputs.

## 5. Data and ML pipelines

Data/ML automation must record:
- source/provider;
- source timestamp;
- ingestion time;
- dataset/version;
- transformation/code version;
- upstream/downstream lineage;
- quality checks;
- freshness status;
- backfill range;
- model/feature version when applicable.

A failed quality/freshness gate must stop downstream promotion.

## 6. Operational automation

Operational workflows may automate:
- health checks;
- incident creation;
- notifications;
- backups;
- retention/cleanup;
- cache warming;
- provider fallback coordination;
- reconciliation jobs;
- report generation;
- security/dependency scans.

They may not hide degraded state or suppress critical evidence.

## 7. Human and Owner gates

Automation may prepare evidence and request approval, but may not auto-grant an Owner-only gate.

Human approval must be explicit where roadmap/governance requires it.

Approval records must include:
- approver identity;
- scope;
- evidence snapshot;
- timestamp;
- result;
- rollback/stop controls where applicable.

## 8. Failure semantics

Use explicit terminal/intermediate states such as:
- `SUCCESS`
- `FAILED_RETRYABLE`
- `FAILED_TERMINAL`
- `DEGRADED`
- `BLOCKED`
- `WAITING_FOR_APPROVAL`
- `CANCELLED`
- `QUARANTINED`

Infrastructure failure must not be reinterpreted as a business or market decision.

## 9. Observability

Minimum workflow telemetry:
- workflow/run ID;
- trigger type;
- parent/child run;
- start/end/duration;
- retries;
- queue delay;
- step status;
- input/output schema validation;
- resource usage;
- errors;
- circuit-breaker state;
- approval waits;
- cancellation;
- data freshness;
- evidence links.

OpenTelemetry-compatible telemetry is preferred for portability.

## 10. Security

- credentials come from approved secret storage only;
- least privilege is mandatory;
- workflow definitions are version controlled;
- webhook/event inputs are authenticated and validated;
- external content is untrusted;
- secret values must be redacted from logs/traces;
- automation cannot widen its own permissions;
- sensitive workflows require explicit environment separation.

## 11. Cost and capacity

Each automation class should define:
- concurrency budget;
- CPU/memory budget;
- queue limit;
- rate limits;
- provider/API quotas;
- storage/retention budget;
- alert threshold for runaway retries/cost.

## 12. Tool-selection policy

Default separation of concerns:

- GitHub Actions: repository CI/governance.
- Temporal candidate: critical durable/stateful workflows.
- Dagster candidate: data/quant/ML asset pipelines and lineage.
- Kestra candidate: event/schedule/ops workflows where a distinct requirement remains.
- n8n candidate: bounded external integrations after license/security review.

Do not install overlapping systems without measured justification.

## 13. Promotion gate

Before production adoption of an automation runtime:
- exact version is pinned;
- license and transitive dependencies are reviewed;
- SBOM/CVE review passes;
- deployment/backup/upgrade strategy exists;
- retry/idempotency tests pass;
- chaos/failure/recovery tests pass;
- observability and redaction are verified;
- capacity/cost benchmark is recorded;
- replacement/exit strategy exists;
- ADR/task approval is complete.

## 14. Phase ownership

- P02: architecture and runtime boundaries.
- P04: CI/CD, dependency/runtime selection and supply-chain controls.
- P05/P06: ingestion, data-quality, freshness, backfill.
- P14/P17/P18: evaluation/training/retraining/promotion pipelines.
- P22: operations, observability, incidents, recovery.
- P23: user-facing workflow status/approval UX where needed.
- P24: final resilience, chaos and rollback validation.

Until those phases authorize implementation, this baseline is research/governance only.

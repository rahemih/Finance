# P22-H — Incident / Postmortem

Task: `FIN-P22-WH-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Define deterministic incident and postmortem artifacts with explicit evidence lineage, ordered timeline, causal findings and corrective-action tracking without granting remediation authority.

## Incident contract

An incident record contains:

- severity: `SEV1..SEV4`;
- lifecycle state: `OPEN / CONTAINED / RECOVERED / CLOSED`;
- explicit lifecycle timestamps;
- bounded impact scopes;
- an ordered event timeline;
- SHA-256 evidence references;
- correlation lineage.

Lifecycle/timeline inconsistencies fail closed.

## Postmortem contract

A postmortem may be created only for a `RECOVERED` or `CLOSED` incident and must include:

- root-cause code and summary;
- bounded contributing factors;
- canonical evidence references;
- at least one corrective action;
- explicit owner role and priority per corrective action;
- mandatory verification requirement.

Corrective actions are registry entries only. They have `execution_authority=false` and `automatic_remediation=false`.

## Privacy and authority boundary

The canonical schema contains no person-name or PII identity fields. It does not execute remediation, mutate network/infrastructure/runtime state, access credentials, or mutate external orders.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-I — SLO / Capacity / Cost Monitoring remains NOT_STARTED until P22-H is canonically closed.

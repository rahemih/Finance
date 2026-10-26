# P22-D — Constrained Self-Healing

Task: `FIN-P22-WD-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Define the deterministic safety boundary for constrained self-healing without granting runtime execution authority.

## Eligibility

A healing plan may be emitted only when all of the following hold:

- P22-C diagnosis is `MATCHED_RULE`;
- severity is `WARNING`;
- operator review is not required;
- system state is `NORMAL` or `DEGRADED`;
- the hypothesis has an explicit pre-approved action rule;
- attempt budget remains available;
- required cooldown has elapsed.

Any missing condition fails closed.

## Pre-approved reference action

The initial canonical allowlist contains one reference-only rule:

- `DATA_FRESHNESS_DEGRADATION` → `RESTART_STATELESS_OBSERVER`;
- rollback reference → `STOP_REPLACEMENT_OBSERVER`;
- max attempts = 1;
- cooldown required;
- post-action validation required.

This is a deterministic planning contract only. The module does not execute a restart, process command, infrastructure change or network operation.

## Safety boundary

- execution mode = `REFERENCE_PLAN_ONLY`;
- execution authority = false;
- external side effects = false;
- restricted system states are not eligible;
- diagnostics requiring operator review are not eligible;
- critical/emergency diagnostics are not eligible;
- runtime state mutation = false;
- automatic risk-policy relaxation = false;
- network = DISABLED;
- credentials = NONE;
- Live execution authority = false.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-E — Backup remains NOT_STARTED until P22-D is canonically closed.

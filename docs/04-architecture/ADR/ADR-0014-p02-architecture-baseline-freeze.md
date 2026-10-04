# ADR-0014 — P02 Architecture Baseline Freeze

Status: ACCEPTED  
Task: `FIN-P02-WI-001`  
Gate: `G2_ARCHITECTURE_FREEZE`

## Context

P02-A through P02-H define the implementable architecture baseline for NEXUS QUANT:

- architecture principles and ADR governance;
- domain/module boundaries;
- data flow, storage, replay and lineage;
- intelligence/signal/probability/explainability;
- independent Risk / Firewall / OMS execution;
- governed Agent runtime authority;
- environment/network/DR topology;
- provisional capacity/cost envelope.

The terminal P02-I review found no unresolved critical architecture risk and all required diagram classes are present.

## Decision

Upon canonical closure of `FIN-P02-WI-001`:

`P02_ARCHITECTURE_BASELINE = FROZEN_G2`

The P02 architecture baseline becomes the binding architecture source for P03/P04 and later implementation phases.

Direct unreviewed semantic changes are forbidden.

Allowed change mechanisms:
- ADR;
- RFC;
- ERRATA for non-semantic factual/typographical corrections;
- ROADMAP ADDENDUM where frozen roadmap scope changes.

## Frozen invariants

The following cannot be weakened silently:

- modular-core-first / avoid premature microservices;
- provider-portable canonical contracts;
- country/location-neutral architecture;
- replay/provenance/versioned historical truth;
- empirical/calibrated probability or unavailable state;
- independent Risk and Pre-Trade Firewall veto;
- no direct strategy/agent/UX broker path;
- stable idempotency and explicit execution uncertainty/reconciliation;
- no blind cross-broker replay;
- no Auto-Promote-to-Live;
- bounded Agent authority and Tool Gateway enforcement;
- A5/A8 veto non-bypassability;
- environment/credential isolation;
- SHADOW no-live-command path;
- reconciliation before resumed risk-increasing execution;
- safety/security/audit controls not shed for cost;
- Live/Auto Trading disabled until later gates.

## Deferred implementation is not architecture incompleteness

The baseline intentionally leaves concrete implementation decisions to later phases:

- P03: Threat model, MFA/RBAC, secrets, admin exposure, security validation.
- P04: Exact runtime/library/database/queue/storage/cloud choices and version pins.
- P05/P06: Real market-data rates, compression and performance measurements.
- P08-P18: Empirical strategy/model/signal validation.
- P20-P22: Execution/operations implementation and recovery drills.
- P24: Controlled real-capital activation.

Those tasks must conform to the frozen P02 contracts or raise a governed architecture change.

## Revalidation triggers

Architecture review/G2 assumptions must be revalidated when:
- domain ownership/interface changes materially;
- provider-specific lock-in enters a core domain;
- Risk/Firewall authority changes;
- execution idempotency/failover semantics change;
- Agent authority or tool-security model changes;
- environment/credential boundaries change;
- capacity envelope is materially exceeded;
- a SEV incident invalidates an assumption;
- later implementation proves an architecture requirement infeasible.

## Consequences

Positive:
- P03/P04 can implement against stable boundaries;
- architecture drift becomes explicit/governed;
- safety-critical authority remains reviewable;
- vendor/technology changes remain possible behind contracts.

Negative:
- later discoveries may require ADR/RFC overhead;
- provisional performance assumptions must be actively replaced by measurements.

## Gate effectiveness

This ADR is effective with canonical P02-I closure.

`G2_ARCHITECTURE_FREEZE = PASS`

`P02_ARCHITECTURE_BASELINE = FROZEN_G2`

Implementation review evidence:
- PR #75 merged as `fd62cf3abdde7f4f00d5102b8170cdd7564bb74e`
- PR Governance `37193927009` = SUCCESS
- post-merge Governance `37193970490` = SUCCESS
- post-merge Branch Hygiene `37193970613` = SUCCESS

## Related artifacts

- `docs/04-architecture/P02-ARCHITECTURE-REVIEW.md`
- `docs/04-architecture/p02-architecture-review.json`
- `docs/04-architecture/P02-ARCHITECTURE-DIAGRAMS.md`
- `docs/00-governance/G2-ARCHITECTURE-FREEZE.md`

# P23-E — Team Collaboration

Task: `FIN-P23-WE-001`  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WE-001-01` / ACQUIRED

## Purpose

P23-E defines audit-friendly collaboration metadata for comments, mentions, assignments and team-workflow approvals.

## Authority boundary

`COLLABORATION_METADATA_ONLY`

A team workflow approval is not:
- Owner phase authorization;
- independent Risk approval/veto;
- execution/order approval;
- P24 production approval.

Assignments never grant RBAC permissions or execution authority.

## Audit model

Events are append-only with deterministic IDs, ordered history and tombstone-only deletion semantics. Each event requires actor, target, timestamp and provenance.

## Safety

No credential access, permission mutation, runtime mutation/remediation, external-order authority, production/P24 activation, Live Trading or Auto Trading.

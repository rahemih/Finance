# P22-F — Restore Drills

Task: `FIN-P22-WF-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Validate the canonical P22-E recovery contract through deterministic reference restore/rebuild drills without performing a real production restore.

## Drill semantics

P22-F consumes a canonical P22-E `BackupManifest`.

- DR0, DR1 and DR2 use `RESTORE` drill semantics only when the backup manifest is eligible.
- DR3 uses `REBUILD` semantics because P22-E defines DR3 as rebuild-only.
- The recovery point is the backup-manifest creation timestamp.
- Reference RPO is measured from recovery point to incident.
- Reference RTO is measured from incident to validation completion.
- Durations use deterministic ceiling-to-seconds conversion.

## Validation

A reference drill cannot pass unless:

- restored/rebuilt content SHA-256 matches the source content hash;
- restore quarantine passes when required by the backup class;
- post-restore reconciliation passes when required, especially for DR0;
- reference RPO target is met when applicable;
- reference RTO target is met.

Malformed timing or invalid identifiers fail closed.

## Claim boundary

A PASS means only that the deterministic reference drill satisfies the canonical architecture contract for the supplied scenario.

It does **not** certify production RPO/RTO, storage infrastructure, network transfer, a real failover, or a real restore. P22-G owns Disaster Recovery.

No real restore execution, storage write, network access, credentials, production mutation or Live execution authority is granted.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-G — Disaster Recovery remains NOT_STARTED until P22-F is canonically closed.

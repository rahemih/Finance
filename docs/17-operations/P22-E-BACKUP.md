# P22-E — Backup

Task: `FIN-P22-WE-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Define a deterministic, rights-aware and content-addressed backup manifest contract for the canonical DR0–DR3 classes without performing any real storage write.

## DR classes and provisional targets

- **DR0 — Execution Authority State:** backup required; provisional RPO target 60 seconds; provisional NORMAL recovery objective 3600 seconds; off-primary copy required; restore quarantine required; post-restore reconciliation required.
- **DR1 — Control / Security State:** backup required; provisional RPO 900 seconds; provisional RTO 14400 seconds; off-primary copy and restore quarantine required.
- **DR2 — Market / Historical / Research Data:** backup required where retention rights permit; provisional RPO/RTO 86400 seconds; off-primary copy and restore quarantine required.
- **DR3 — Rebuildable Derived State:** backup is not required; RPO is not applicable when fully reproducible; provisional RTO 172800 seconds; canonical result is rebuild-only.

These are architecture targets, not measured results. P22-F Restore Drills owns empirical recovery validation.

## Integrity and failure-domain rules

Every reference manifest binds a source reference, source content SHA-256, explicit version, timestamp, byte size, DR class, rights status and logical failure domains.

For DR0–DR2, a recovery copy in the same logical failure domain does **not** count as disaster-recovery backup and fails closed.

Restored content remains untrusted until integrity validation and restore-quarantine checks pass.

## Rights boundary

Raw licensed/provider content may be included only when retention is explicitly allowed. `FORBIDDEN` and `UNVERIFIED` fail closed. `DERIVED_ONLY` is accepted only when the manifest states that raw licensed content is absent.

Backup cannot bypass provider retention or licensing obligations.

## Authority boundary

P22-E creates a reference manifest only:

- no real backup write;
- no storage/cloud vendor selection or provisioning;
- no network transfer;
- no account or secret material;
- no production mutation;
- no restore execution;
- no measured RPO/RTO claim;
- no Live execution authority.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-F — Restore Drills remains NOT_STARTED until P22-E is canonically closed.

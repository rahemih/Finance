# P23-F — Notification Engine

Task: `FIN-P23-WF-001`  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WF-001-01` / ACQUIRED

## Objective

Define deterministic notification routing, quiet-hours, deduplication and escalation metadata for canonical NEXUS QUANT events without granting external-delivery, credential, execution, Owner/Risk or production authority.

## Upstream binding

- P11-G supplies canonical alert severities: INFORMATIONAL / IMPORTANT / CRITICAL / SUPPRESSED.
- P23-E supplies team collaboration/audit semantics.
- P23-F does not reinterpret either authority boundary.

## Routing

- canonical channel: IN_APP only;
- INFORMATIONAL / IMPORTANT may be deferred during quiet hours;
- CRITICAL bypasses quiet hours to IN_APP and emits ON_CALL_QUEUE escalation metadata;
- SUPPRESSED never routes to delivery;
- notification and deduplication identities are deterministic.

## External delivery

Email, SMS, push, webhook and third-party delivery providers remain out of scope for this canonical workstream. No credentials are provisioned and provider = NOT_SELECTED.

## Governance boundary

Escalation metadata cannot satisfy Owner authorization, independent Risk veto, execution approval or P24 production approval.

## Safety

No permission mutation, external-order authority, runtime mutation/remediation, credentials, production/P24 activation or Live/Auto trading authority.

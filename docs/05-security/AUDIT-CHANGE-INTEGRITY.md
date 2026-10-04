# NEXUS QUANT — Audit & Change Integrity Baseline

STATE = P03-E CANONICAL_BASELINE
TASK = `FIN-P03-WE-001`
LINEAR = `HOS-167`
BASELINE = `FROZEN_G2`
DATE = 2026-10-04

## 1. Purpose

Define the canonical audit/evidence and high-risk change-integrity policy for NEXUS QUANT.

Audit exists to reconstruct what happened, who/what caused it, under which authority and evidence, and whether the record has been altered.

This task defines the contract only. It does not provision SIEM, WORM storage, object lock, immutable database, signing service or archival infrastructure.

## 2. Evidence stream classes

### L1 — Security Audit

Examples:
- authentication/MFA/recovery;
- authorization allow/deny;
- role/permission changes;
- secret/key lifecycle;
- security veto/halt;
- privileged administrative sessions;
- incident/break-glass activity.

Integrity priority: CRITICAL.

### L2 — Governance / Change Audit

Examples:
- Task Contract/lock lifecycle;
- Human Gate;
- policy/config/model/version promotion;
- security/risk threshold changes;
- environment promotion;
- exception creation/expiry.

Integrity priority: CRITICAL.

### L3 — Execution / Financial Audit

Examples:
- SignalCandidate references;
- RiskVerdict / FirewallVerdict;
- execution intent;
- route attempt;
- provider acknowledgement/fill/reject;
- reconciliation;
- position/exposure/kill-switch transitions.

Integrity priority: CRITICAL.

### L4 — Data / Evidence Provenance Audit

Examples:
- source ingest identifiers;
- data correction/revision;
- quarantine/quality decisions;
- dataset/feature/model lineage;
- replay/evaluation evidence.

Integrity priority: HIGH.

### L5 — Operational / Reliability Events

Examples:
- health transitions;
- dependency outage;
- queue/circuit-breaker state;
- degraded/safe-mode entry/exit;
- backup/restore workflow.

Integrity priority: HIGH.

### L6 — Debug / Diagnostic Logs

Purpose:
- troubleshooting.

Rules:
- not automatically authoritative evidence;
- may be sampled/short-lived;
- must not contain secrets;
- must not be used as the sole proof for HIGH/CRITICAL decision history.

## 3. Canonical audit event envelope

Every canonical audit event has:

- `audit_event_id` — globally unique stable identifier;
- `event_type`;
- `event_schema_version`;
- `event_time`;
- `source_time` when distinct;
- `receive_time`;
- `observed_at`;
- `time_confidence`;
- `actor_principal_id`;
- `actor_type` — HUMAN / AGENT / SERVICE / CI / EXTERNAL;
- `actor_session_or_workload_ref`;
- `action`;
- `target_resource`;
- `environment`;
- `task_id` / `run_id` / `correlation_id` where applicable;
- `policy_version`;
- `authorization_decision_id` where applicable;
- `human_gate_id` where applicable;
- `risk_verdict_id` / `firewall_verdict_id` where applicable;
- `before_ref` / `after_ref` or normalized change digest where applicable;
- `result`;
- `reason_code`;
- `evidence_refs`;
- `producer_id`;
- `sequence_or_chain_position`;
- `previous_digest` where chain mode applies;
- `event_digest`;
- optional signature/attestation reference when later implemented.

No raw secret is an audit field.

## 4. Identity and attribution

Attribution must identify the actual initiating principal and execution path.

Never collapse all actions into:
- “admin”;
- “system”;
- shared account;
- shared API key;
- anonymous automation.

For agent/tool actions record:
- initiating human/task if any;
- agent identity;
- tool/service identity;
- normalized requested action;
- authorization decision;
- outcome.

For delegated operations, preserve initiator → delegator → executor chain.

Source IP/device/location can be context but is not identity.

## 5. Append-only and tamper-evident direction

Canonical evidence is logically append-only.

Rules:
- prior canonical event meaning is never silently edited;
- corrections are new linked events;
- deletion is not normal business mutation;
- retention/disposal is explicit governed lifecycle, not ad-hoc delete;
- canonical manifests support integrity verification;
- digest chaining or equivalent tamper-evidence is required for critical evidence domains;
- immutable/read-only copies are required as a future implementation direction for critical audit;
- all audit read/export/admin access is itself audited.

A digest proves integrity only when its trust anchor/manifests are independently protected; a hash stored beside mutable data is insufficient by itself.

## 6. Digest-chain direction

Conceptual chain:

`digest_n = H(canonical_event_n || digest_(n-1) || stream_id || schema_version)`

Requirements:
- deterministic canonical serialization;
- cryptographic hash selected later in P04;
- explicit stream/partition identity;
- chain checkpoints/manifests;
- independent protection/signing/attestation direction for checkpoints;
- missing, reordered or modified events must be detectable;
- chain repair means append a recovery/correction record, not rewrite history.

This is an architecture contract, not a claim that cryptographic chaining is currently deployed.

## 7. Audit writer / reader / administrator separation

### Writers
May append only authorized event classes.
Cannot modify/delete prior canonical events.

### Readers / Investigators
May query permitted evidence.
Cannot alter canonical history.

### Audit Platform Administrators
May operate storage/index/retention mechanisms.
Should not automatically gain business/execution authority.
Administrative actions against audit infrastructure are themselves recorded to an independently protected audit path when later implemented.

### Evidence Approvers / A10
May verify completeness/integrity and produce evidence manifests.
Cannot fabricate missing source events or override A8 security state.

## 8. Sensitive-data policy

Never directly log:
- passwords;
- MFA secrets;
- private keys;
- API keys;
- raw broker/exchange credentials;
- full session/access/refresh tokens;
- secret-manager plaintext;
- unnecessary personal/sensitive data.

Prefer:
- secret handle;
- token/session hash or bounded reference;
- principal ID;
- masked account identifier where required;
- normalized reason code;
- content digest instead of sensitive payload.

Audit data is security-sensitive even when it contains no secrets.

## 9. Time semantics

Use all relevant clocks explicitly:
- source/event time;
- receive time;
- observed-at time;
- persisted/ingested time when needed.

Record:
- clock source;
- synchronization/offset state where known;
- time confidence.

For an externally controlled client/device timestamp, do not treat its timestamp as trusted solely because it is present.

Ordering-critical streams may require monotonic sequence in addition to wall-clock time.

## 10. High-risk change classes

### C1 — Security Authority Change — CRITICAL

Examples:
- privileged role grant/revoke;
- MFA/recovery/security policy weakening;
- secret/KMS policy;
- A8 veto policy;
- private admin exposure;
- audit protection policy.

Requirements:
- phishing-resistant privileged auth;
- exact before/after digest;
- reason/evidence;
- Human Gate where governance requires;
- maker/checker for selected highest-risk cases;
- rollback plan;
- post-change verification.

### C2 — Risk / Trading Authority Change — CRITICAL

Examples:
- risk ceiling;
- leverage/exposure limit;
- Firewall rule;
- kill-switch semantics;
- CANARY/LIVE activation;
- broker execution permissions.

Requirements:
- A5 and A8 involvement per authority;
- Owner/Human Gate where required;
- maker/checker before production-capable activation;
- exact version/digest;
- no self-approval by the single implementing actor for highest-risk production changes.

### C3 — Credential / Secret Change — CRITICAL

Examples:
- issue/rotate/revoke execution credential;
- change withdrawal/trading permissions;
- KMS/signing/recovery key control.

Requirements:
- P03-C policy;
- privileged step-up;
- dual-control/maker-checker for policy-defined production critical credentials;
- secret value never logged.

### C4 — Environment / Network Exposure Change — HIGH/CRITICAL

Examples:
- expose admin endpoint;
- change Z4/Z5/Z7 inbound rule;
- create cross-environment route;
- production egress change.

Requirements:
- exact rule/config digest;
- exposure diff;
- security approval for high-risk change;
- verification that forbidden paths remain closed.

### C5 — Model / Strategy / Configuration Promotion — HIGH

Examples:
- model/config/strategy version promoted to higher environment.

Requirements:
- immutable artifact/version;
- evaluation evidence;
- task/run;
- before/after version;
- higher gate for CANARY/LIVE.

### C6 — Data / Provenance Override — HIGH

Examples:
- quarantine override;
- historical correction;
- provider/source substitution.

Requirements:
- never rewrite prior observation;
- append correction/override;
- preserve old/new source/evidence.

## 11. Maker/checker direction

Maker/checker is required by policy for actions where compromise or error by one privileged actor could directly:
- enable LIVE/CANARY authority;
- weaken/disable A5/A8/Firewall protection;
- grant critical credential permissions;
- expose Z4/Z5/Z7 publicly;
- destroy/disable critical audit evidence;
- perform equivalent critical security-authority escalation.

Principles:
- maker and checker are independently attributable;
- checker sees exact action/resource/environment/digest;
- approval expires and is one-use;
- material change after approval invalidates it;
- emergency path is separately audited and reviewed.

P03-E defines the rule; exact implementation/product is later.

## 12. Human Gate integrity

Human Gate evidence binds:
- approval ID;
- approver principal;
- maker/requester principal;
- task/run;
- exact action;
- target resource;
- environment;
- normalized arguments/config digest;
- before/after version/digest where applicable;
- evidence references;
- timestamp;
- expiry;
- single-use state;
- resulting authorization/change ID.

A Human Gate cannot:
- authorize a different argument set;
- survive material configuration drift;
- suppress A5/A8 veto;
- be replayed after use/expiry;
- be copied from lower environment to authorize higher environment.

## 13. Audit completeness by critical path

### Authentication / Authorization
Record auth success/failure, MFA/recovery, session/role changes, sensitive deny/allow.

### Governance
Record task/lock/gate/approval/exception lifecycle.

### Risk / Execution
Record candidate/verdict/intent/firewall/order lifecycle/reconciliation/kill-switch.

### Secrets
Record metadata-level issue/resolve/use/rotate/revoke/deny; never plaintext.

### Network / Admin
Record privileged session start/end, target/action, policy result, exposure-policy changes.

### Supply Chain
Record source revision, dependency/artifact/SBOM/provenance/signature/promotion decisions once implemented.

### Backup / Restore
Record manifest, restore source, integrity validation, security revalidation, reconciliation and re-enable decisions.

## 14. Audit failure policy

Not all logging failures should cause the same operational response.

For HIGH/CRITICAL privileged mutation or production-capable financial action:
- if required canonical audit/evidence cannot be durably accepted within policy tolerance, block or enter fail-closed/safe mode.

For lower-risk read/debug operations:
- availability may continue with bounded local buffering/degraded telemetry when safe.

Rules:
- logging failure must never silently convert a denied action to allowed;
- buffers have bounded size/time;
- overflow is explicit alert/state;
- audit outage itself is a security event;
- recovery reconciles buffered vs durable evidence.

## 15. Retention / disposal

Exact retention periods are deferred because legal, contractual, licensing, privacy and operational obligations are not yet resolved.

Canonical requirements:
- retention policy is class-specific and versioned;
- critical evidence cannot be deleted before required period;
- disposal is authorized and audited;
- legal/security hold can suspend normal disposal;
- raw market/data licensing restrictions are respected;
- backups/copies/exports follow the same lifecycle rules;
- country/location is not assumed to define retention.

## 16. Audit access / export

Read/export follows least privilege.

Export of critical evidence:
- is attributable;
- has scope/reason;
- preserves integrity metadata;
- is recorded;
- redacts data according to policy.

Bulk export is not granted by ordinary operator access.

## 17. Integrity verification

Future verifier must support:
- schema validation;
- required-field completeness;
- digest recomputation;
- chain/checkpoint continuity;
- duplicate/missing/reordered detection where sequence applies;
- referenced artifact existence/hash validation;
- signature/attestation verification when implemented;
- clock/time-confidence review;
- access-control review.

Independent verification must not rely solely on the same mutable store being audited.

## 18. Alert-worthy events

At minimum:
- audit writer unexpectedly stops;
- gap/chain mismatch;
- unexpected delete/retention action;
- unauthorized audit read/export;
- privileged role/security policy change;
- repeated Human Gate replay rejection;
- A5/A8 override attempt;
- Z4/Z5/Z7 exposure change;
- critical secret/credential change;
- audit clock/time-quality degradation;
- log volume anomaly/resource exhaustion attempt.

## 19. Downstream implementation ownership

P04:
- concrete event schema package;
- log/evidence libraries;
- hash/signature/provenance implementations;
- CI verification.

P22:
- centralized observability, alerting, audit health, incident/forensic workflow;
- retention/backup integration.

P23:
- application security/audit event generation;
- account/admin change UX.

P24:
- independent audit completeness/integrity review before production;
- maker/checker/Human Gate production evidence.

## 20. Required downstream tests

- modify canonical audit record → integrity mismatch detected;
- delete/reorder event → gap detected;
- writer cannot mutate prior event;
- reader cannot delete event;
- raw secret/token logging negative tests;
- high-risk config change without required checker → DENY;
- reused/expired Human Gate → DENY;
- approved digest differs from applied digest → DENY;
- A8/A5 override attempt → recorded + DENY;
- critical audit sink unavailable → HIGH/CRITICAL mutation blocked;
- time/source-confidence degradation visible;
- export operation is audited;
- corrected data produces linked correction rather than history rewrite.

## 21. Current implementation state

Canonical audit storage: NOT_PROVISIONED  
SIEM: NOT_SELECTED / NOT_PROVISIONED  
WORM/object-lock: NOT_SELECTED / NOT_PROVISIONED  
Digest chain/signature service: NOT_IMPLEMENTED  
Jurisdiction-specific retention: NOT_DEFINED  
Production maker/checker mechanism: NOT_IMPLEMENTED  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This artifact is a canonical policy baseline, not a deployed-control claim.

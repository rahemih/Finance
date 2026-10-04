# NEXUS QUANT — Incident Response & Emergency Access Baseline

STATE = P03-G CANONICAL_BASELINE
TASK = `FIN-P03-WG-001`
LINEAR = `HOS-170`
BASELINE = `FROZEN_G2`
DATE = 2026-10-04

## 1. Purpose

Define the canonical security incident, containment, emergency-access and safe-recovery contract for NEXUS QUANT.

The model aligns to NIST SP 800-61 Rev.3 / CSF 2.0 concepts and applies them to financial-system-specific failure modes.

P03-G does not operate a real SOC, on-call rota, SIEM, EDR, paging, forensic platform or legal-notification program.

## 2. Incident principles

1. Preserve safety before availability.
2. A8 Security may halt affected security-sensitive scope.
3. A5 Risk remains authoritative for risk veto and exposure safety.
4. A6 Execution owns execution truth/reconciliation, not strategy/agents.
5. UNKNOWN external execution state is an incident condition when exposure may be ambiguous.
6. Recovery never restores privilege or execution authority automatically.
7. Evidence preservation starts at declaration/containment, not after recovery.
8. Break-glass is bounded recovery authority, not a bypass.
9. Raw secrets are never copied into incident tickets/chat/evidence.
10. Country/location is not assumed for reporting/notification obligations.

## 3. Severity

### SEV-0 — Emergency / Potential Material Capital or Security Loss

Examples:
- unauthorized or potentially unauthorized live-capable execution;
- confirmed critical credential compromise with execution/security authority;
- A5/A8/Firewall bypass;
- destructive compromise of audit/recovery truth;
- unreconciled external exposure with material downside;
- broad privileged account takeover.

Response:
- immediate affected-scope or global halt;
- incident commander assigned;
- A8/A5/A6/A9/A10 engaged as relevant;
- preserve evidence;
- no normal recovery until explicit revalidation.

### SEV-1 — Critical

Examples:
- privileged compromise without confirmed execution;
- compromised dependency/build artifact used in high-trust environment;
- major data poisoning affecting decision eligibility;
- Z4/Z5/Z7 exposure;
- audit integrity failure on critical stream;
- ransomware/destructive event in critical domain.

### SEV-2 — High

Examples:
- bounded service compromise;
- provider integrity anomaly;
- repeated Human Gate replay/authorization abuse;
- secret leak with limited scope;
- significant availability attack.

### SEV-3 — Moderate

Examples:
- contained suspicious activity;
- non-critical policy violation;
- recoverable dependency/security control degradation.

### SEV-4 — Low / Observation

Examples:
- security-relevant anomaly requiring tracking but no confirmed compromise.

Severity can increase as evidence changes.

## 4. Lifecycle

### Prepare / Govern

Before incident:
- roles and vetoes documented;
- contact/escalation placeholders defined;
- access/recovery mechanisms tested later;
- evidence/log requirements defined;
- backups/recovery artifacts identified;
- tabletop scenarios maintained.

### Detect

Sources:
- security/audit alert;
- user/operator report;
- provider anomaly;
- agent/tool policy violation;
- data quality divergence;
- execution reconciliation mismatch;
- supply-chain scanner/provenance failure;
- backup/restore integrity issue.

### Analyze / Declare

Record:
- incident ID;
- initial severity;
- affected zones/environments/resources;
- confidence;
- suspected actor/vector;
- financial/execution exposure;
- credential/data/artifact scope;
- evidence references;
- commander/owners.

Do not wait for perfect certainty before containing credible CRITICAL risk.

### Contain

Possible actions:
- A8 security halt;
- A5 risk halt/reduction;
- revoke session/role;
- revoke/rotate credential;
- disable tool/service integration;
- quarantine data/provider/model/artifact;
- block network route;
- halt promotion;
- pause affected OMS/broker route;
- switch to safe/read-only/degraded mode.

Containment must not destroy evidence unnecessarily.

### Eradicate / Remediate

Examples:
- remove compromised identity/access;
- patch/replace dependency;
- rotate credentials;
- repair policy/config;
- rebuild artifact from trusted source;
- re-establish clean data source;
- remove malicious tool/MCP;
- repair audit/backup chain through governed append-only recovery evidence.

### Recover

Recovery is staged:
1. verify root cause/containment;
2. validate identity/security policy;
3. validate secrets/credentials;
4. validate data/provenance;
5. validate artifact/supply-chain evidence;
6. validate audit integrity;
7. reconcile external provider/broker truth;
8. recompute risk/security state;
9. enable read-only/limited service first where appropriate;
10. only later re-enable risk-increasing execution under fresh gate evidence.

### Post-Incident

- timeline;
- root cause;
- impact;
- controls that worked/failed;
- evidence completeness;
- corrective tasks;
- threat-model/policy updates;
- test/drill additions;
- exception removal;
- closure approval.

## 5. Incident command roles

### A8 Security

Authority:
- security containment;
- security veto;
- revoke compromised security/access path;
- classify security compromise.

Cannot:
- raise A5 risk limits;
- directly place broker orders.

### A5 Risk

Authority:
- risk halt/reduction;
- exposure safety decision;
- approve no risk-increasing recovery until risk truth is sufficient.

### A6 Execution

Authority:
- order/provider lifecycle truth;
- reconciliation;
- halt/reroute eligibility within governed policy.

Cannot:
- classify security credential trustworthy after A8 veto.

### A9 Operations

Authority:
- diagnostics;
- service recovery coordination;
- backup/restore execution later;
- safe-mode operation.

### A10 Evidence / Audit

Authority:
- evidence completeness/integrity review;
- incident timeline/evidence manifest.

Cannot fabricate missing events.

### A0 Governance / Incident Coordination

Coordinates tasks, owners, evidence and gates.
Cannot override A5/A8 veto.

## 6. Credential compromise playbook

Trigger:
- confirmed/suspected plaintext exposure;
- suspicious use;
- provider notice;
- unauthorized secret resolve;
- signing/session key compromise.

Flow:
1. classify secret/key and scope;
2. halt affected privileged/execution path when necessary;
3. revoke/disable exposed credential;
4. invalidate affected sessions/tokens;
5. issue/rotate replacement through P03-C policy;
6. search evidence for unauthorized use;
7. validate old credential rejection;
8. reconcile external provider state;
9. resume only after security/risk approval.

Never wait for log cleanup before revocation.

## 7. Execution / broker incident

Triggers:
- timeout / ambiguous acknowledgement;
- duplicate/collision suspicion;
- reconciliation mismatch;
- provider outage/inconsistency;
- unauthorized order/fill;
- compromised broker API credential;
- symbol/precision/capability anomaly.

Rules:
- UNKNOWN is neither failure nor success;
- no blind retry/reroute;
- one unresolved execution-capable route per logical exposure;
- fetch/reconcile provider truth;
- halt affected new risk-increasing orders;
- revoke credential if compromise suspected;
- recompute account/position/exposure;
- fresh Risk + Firewall + Security approval required before new route.

## 8. Data poisoning / integrity incident

Triggers:
- cross-provider divergence;
- replay/staleness;
- impossible sequence/gaps;
- macro/news revision leakage;
- source compromise;
- provenance mismatch.

Actions:
- quarantine affected source/data range;
- mark downstream evidence/features/signals ineligible;
- preserve raw observation;
- switch to alternate approved source only through policy;
- identify affected decisions/backtests;
- replay/rebuild from trusted evidence if required;
- do not silently overwrite historical data.

## 9. Agent / model / MCP compromise

Triggers:
- prompt injection causes unauthorized intent;
- tool definition/output poisoning;
- unexpected secret exposure;
- model/provider behavior violates policy;
- checkpoint/memory poisoning.

Actions:
- remove sensitive tool capability;
- quarantine provider/tool/MCP;
- invalidate affected checkpoint/session;
- revoke leaked credentials;
- preserve prompt/tool/evidence safely without reproducing secrets;
- revalidate Task/Agent/Tool policy;
- resume with bounded clean state.

Model fallback does not expand authority.

## 10. Supply-chain incident

Triggers:
- dependency/action/package compromise;
- source tampering;
- CI token/runner compromise;
- provenance/signature mismatch;
- malicious artifact.

Actions:
- halt promotion;
- identify affected source/build/artifact digests;
- revoke CI/signing identities as applicable;
- invalidate affected artifacts;
- repair workflow/dependency/source;
- trusted rebuild;
- regenerate SBOM/provenance/signature;
- verify before resume.

## 11. Audit integrity incident

Triggers:
- missing/reordered critical events;
- digest/checkpoint mismatch;
- unauthorized delete/export;
- audit sink loss during critical action;
- suspicious clock/time manipulation.

Actions:
- preserve independent copies;
- restrict privileged mutation if evidence trust is insufficient;
- identify affected time/window/streams;
- use source/provider/CI evidence for reconstruction without rewriting history;
- append recovery/correction evidence;
- treat unexplained critical gaps as unresolved security state.

## 12. Ransomware / destructive event

Actions:
- isolate affected workloads/storage;
- revoke compromised identities;
- protect unaffected backup/recovery domain;
- preserve forensic evidence;
- validate backup manifests/integrity before restore;
- restore to quarantine/staging;
- rotate/revalidate secrets;
- reconcile provider/broker truth;
- verify security/audit/data state;
- only then permit staged recovery.

A restored system is not automatically trusted.

## 13. Availability / DoS incident

Priorities:
- preserve Risk/Security/Audit/Reconciliation/Kill-Switch paths;
- shed discretionary research/AI workload first;
- bounded queues/retries/circuit breakers;
- safe/read-only mode where appropriate;
- never keep execution running merely to preserve availability if safety truth is unavailable.

## 14. Emergency / break-glass access

Break-glass is permitted only for containment/recovery.

Requirements:
- unique accountable principal;
- strongest available authentication;
- exact environment/resource/action scope;
- time-bounded;
- minimal privilege;
- reason/incident ID;
- high-severity audit;
- credential/session revoked after use;
- post-use review.

Forbidden:
- shared anonymous root/admin password as normal path;
- bypass A5/A8;
- disable audit without independent emergency evidence;
- enable LIVE;
- direct discretionary broker order outside canonical execution path.

If primary identity service is unavailable, alternate emergency access must still preserve separate identity/evidence and later revalidation.

## 15. Kill-switch / safe-mode semantics

Possible scopes:
- tool/provider;
- agent;
- data source;
- symbol/instrument;
- account/provider route;
- execution system;
- environment;
- global.

Kill/halt:
- must be fast and attributable;
- cannot itself silently liquidate/close positions unless a separately approved deterministic emergency policy defines that action;
- records reason/scope/time/actor;
- persists across restart until explicit governed release where required.

## 16. Evidence preservation

Incident evidence:
- uses P03-E canonical event/evidence rules;
- records custody/export;
- hashes/manifests collected artifacts when possible;
- preserves original raw evidence;
- avoids altering source systems more than containment requires;
- never puts raw secrets in tickets/chat.

Evidence uncertainty is explicitly recorded.

## 17. Communications

P03-G defines communication classes, not legal timelines.

Internal:
- incident commander;
- security/risk/execution/ops/evidence owners;
- Owner/Governance when severity/policy requires.

External later:
- provider/broker support;
- cloud/tool vendors;
- affected users/customers;
- regulators/law enforcement/insurers if applicable.

Trigger and timing are deferred to actual jurisdiction, contractual obligations and production operating model.

## 18. Recovery gates

Before privileged or execution re-enable:
- compromised principal removed/revalidated;
- sessions/authenticators revalidated;
- affected secrets rotated/revalidated;
- network/admin path validated;
- artifacts/provenance verified;
- audit chain/gaps assessed;
- data quality/provenance restored;
- provider/broker/account truth reconciled;
- A8 security state permits;
- A5 risk state permits;
- required Human Gate/Owner evidence is fresh;
- incident residual risk documented.

## 19. Drill matrix

Required future tabletop/technical drills:
- privileged account takeover;
- broker credential leak;
- execution timeout → UNKNOWN;
- duplicate-order suspicion;
- provider market-data poisoning;
- prompt-injection/tool abuse;
- malicious dependency/action;
- audit chain break;
- ransomware + restore;
- IdP outage requiring break-glass;
- Z4/Z5 network exposure;
- simultaneous provider + telemetry degradation.

Each drill produces evidence, gaps and remediation tasks.

## 20. Current implementation state

SOC/on-call: NOT_OPERATED_BY_P03-G  
SIEM/EDR/paging: NOT_PROVISIONED  
Forensic platform: NOT_SELECTED  
Production emergency credential: NONE  
Production accounts/credentials: NONE  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This artifact defines the baseline only.

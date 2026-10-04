# NEXUS QUANT — Canonical Threat Model

STATE = P03-A CANONICAL_BASELINE
TASK = FIN-P03-WA-001
LINEAR = HOS-163
BASELINE = FROZEN_G2
DATE = 2026-10-04

## 1. Purpose and scope

This document defines the architecture-level threat model for NEXUS QUANT against the frozen G2 architecture.

It covers:
- identity, session and privilege threats;
- market-data integrity, freshness, replay and provenance threats;
- agent/LLM prompt injection, tool abuse and model/provider compromise;
- Risk / Pre-Trade Firewall veto bypass attempts;
- execution duplication, reroute and reconciliation uncertainty;
- secrets and credential misuse;
- CI/dependency/SBOM/build-provenance threats;
- observability, audit, backup and recovery tampering;
- availability and resource-exhaustion threats.

It does not claim any P03/P04/P22/P23/P24 control is already implemented.

Live Trading = DISABLED.
Auto Trading = DISABLED.
Accounts / credentials / funding / orders = NONE.
Country / location is not a security-architecture dependency.

## 2. Threat-model method

Primary method:
- architecture-first Data Flow / Trust Boundary review;
- STRIDE categories: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege;
- finance/trading abuse cases;
- AI/agent abuse cases;
- software-supply-chain and recovery-integrity abuse cases.

Security objectives:
- CONFIDENTIALITY;
- INTEGRITY;
- AVAILABILITY;
- AUTHENTICITY;
- AUTHORIZATION;
- NON_REPUDIATION;
- REPLAY_RESISTANCE;
- FAIL_CLOSED_SAFETY;
- RECOVERABILITY;
- PROVENANCE.

Severity is architecture risk, not exploit-score precision:
- CRITICAL — plausible compromise can bypass a safety boundary, create unauthorized execution/capital movement risk, subvert security authority, or destroy trustworthy recovery/audit without an independent compensating control;
- HIGH — material compromise of identity, data integrity, execution correctness, secrets, supply chain, audit or availability with significant system-wide impact;
- MEDIUM — meaningful but bounded impact, or requires stronger preconditions/limited scope;
- LOW — limited direct impact and normally requires chaining.

Every HIGH/CRITICAL item has an owning downstream workstream.

## 3. Protected assets

### A01 — Owner/team identities and sessions
Objectives: confidentiality, authenticity, authorization, availability.

### A02 — Role/permission policy
Includes RBAC, Human Gate bindings, agent/tool capability policy and environment authority.
Objectives: integrity, authorization, non-repudiation.

### A03 — Secrets and credential handles
Includes provider/broker/API/model/service credentials and secret-manager metadata.
Objectives: confidentiality, integrity, availability.

### A04 — Security/Risk veto state
Includes A8 Security veto, A5 Risk veto, kill switches and fail-closed state.
Objectives: integrity, availability, non-repudiation.

### A05 — Market/reference/macro/news/on-chain inputs
Objectives: integrity, provenance, freshness, replay resistance, availability.

### A06 — Canonical events, raw evidence and quality verdicts
Objectives: integrity, provenance, replayability, availability.

### A07 — Feature/evidence/replay/model artifacts
Objectives: integrity, provenance, reproducibility, availability.

### A08 — Signal/Risk/Firewall decisions
Objectives: integrity, authenticity, non-repudiation, replay resistance.

### A09 — Execution intents, orders, fills, positions and reconciliation state
Objectives: integrity, authenticity, idempotency, availability, recoverability.

### A10 — Audit/evidence/telemetry
Objectives: integrity, non-repudiation, availability, recoverability.

### A11 — Source, dependencies, CI/CD artifacts, SBOM and provenance
Objectives: integrity, authenticity, provenance, availability.

### A12 — Backup/restore manifests and recovery state
Objectives: confidentiality where required, integrity, recoverability, provenance.

## 4. Threat actors

- external internet attacker;
- credential thief / session hijacker;
- malicious or compromised dependency maintainer;
- compromised CI runner/workflow/token;
- compromised market-data/news/model/tool provider;
- malicious or poisoned external content source;
- compromised MCP/tool server;
- malicious insider or compromised owner/operator endpoint;
- compromised agent/model runtime;
- bot/resource-exhaustion attacker;
- broker/exchange/API compromise or inconsistent external state;
- accidental authorized user causing dangerous state due to weak guardrails.

This model treats provider compromise and operator mistakes as first-class scenarios, not only deliberate attackers.

## 5. Trust boundaries

The frozen G2 trust zones are:

- Z0 User Edge;
- Z1 Application Ingress;
- Z2 Control Plane;
- Z3 Data Plane;
- Z4 Execution Enclave;
- Z5 Security / Secrets;
- Z6 Observability / Audit;
- Z7 Backup / DR.

External boundaries:
- market-data / macro / news / on-chain providers;
- model and tool services;
- MCP servers;
- GitHub / CI / dependency registries;
- future broker/exchange APIs;
- notification channels.

No public, UX, strategy, LLM or agent text path may directly reach broker/exchange execution.

## 6. Non-negotiable security invariants

1. Tool availability is never permission.
2. A0 routing/agent consensus/model fallback cannot override A5 Risk or A8 Security veto.
3. Signal/Strategy/Agent/UX cannot bypass Risk → Firewall → OMS.
4. Unknown critical security, data or execution truth fails closed.
5. Raw secrets do not enter model prompts, ordinary logs, Linear text, audit payloads or analytical datasets.
6. Future execution credentials are environment-bound and least-privilege; withdrawal/transfer permission is disabled/not requested where separable.
7. DEV/TEST/RESEARCH/DEMO/SHADOW cannot write CANARY/LIVE authority or state.
8. SHADOW has no live command path.
9. External web/news/email/PDF/repository/MCP/tool content is untrusted data and cannot change policy, authority or tool permissions.
10. Provider timeout/missing acknowledgement is not proof of non-execution; UNKNOWN must reconcile before retry/reroute.
11. One unresolved execution-capable route per logical exposure is the default.
12. Audit/evidence history cannot be silently rewritten to match current state.
13. Market/macro corrections and revisions append/version truth; they do not erase what was previously observed.
14. Restored execution state cannot authorize new risk-increasing orders until broker truth, policy, security and Risk/Firewall state are reconciled.
15. Build/provenance/signature mismatch fails closed once the corresponding P04 control is activated.
16. Security exceptions require explicit owner, scope, evidence, expiry and compensating control.
17. Budget/cost pressure may shed discretionary research, never Risk/Security/Audit/Reconciliation/Kill-Switch controls.
18. No production activation is inherited from earlier gates; later environment/capital escalation requires fresh evidence.

## 7. Threat register summary

The canonical machine-readable register is in docs/05-security/threat-model.json.

### Identity / authorization

- T001 CRITICAL — privileged account/session takeover.
  Control direction: phishing-resistant MFA, short-lived sessions, device/risk signals, step-up auth, session revocation, privileged-action re-auth.
  Owner: P03-B/P03-G/P23-H.

- T002 CRITICAL — RBAC/authorization bypass or confused-deputy action crossing user/agent/tool authority.
  Control direction: deny-by-default authorization, resource/action/environment binding, centralized policy enforcement, negative tests.
  Owner: P03-B/P03-E/P04-C/P23-H.

- T003 HIGH — cross-environment privilege escalation or credential/state reuse.
  Control direction: distinct identities/credentials/state, explicit environment claims, promotion checks.
  Owner: P03-B/P03-C/P03-D/P04-D.

- T004 HIGH — Human Gate replay, scope substitution or approval reuse.
  Control direction: approval ID + argument digest + environment/resource binding + expiry + one-use semantics.
  Owner: P03-B/P03-E/P04-C.

### Secrets / credentials

- T005 CRITICAL — broker/exchange/API credential exfiltration.
  Control direction: secret handles, KMS/secret manager, no raw secret in model context, audit, emergency revoke.
  Owner: P03-C/P03-G/P04-D/P22-H.

- T006 CRITICAL — over-privileged execution credential with withdrawal/transfer capability.
  Control direction: trading-only permissions, no withdrawal permission, account/provider scope validation.
  Owner: P03-C/P20/P24.

- T007 HIGH — secret leakage through logs, traces, prompts, crash dumps or evidence.
  Control direction: structured redaction, allowlisted telemetry fields, DLP/secret scanning, safe error handling.
  Owner: P03-C/P03-E/P04-C/P22-A.

### Agent / LLM / tool plane

- T008 CRITICAL — prompt injection causes sensitive tool invocation or policy bypass.
  Control direction: deterministic Tool Gateway, untrusted-content labeling, allowlisted tools, typed inputs, capability intersection, A8 veto.
  Owner: P03-A/P03-B/P03-E/P04-C/P04-E.

- T009 CRITICAL — malicious/compromised MCP/tool server poisons instructions, results or tool definitions.
  Control direction: allowlisted servers, schema validation, server/resource identity, tool filtering, output sanitization, quarantine.
  Owner: P03-F/P04-C/P04-E.

- T010 HIGH — excessive agency grants unnecessary write/delete/financial capability.
  Control direction: least functionality, least privilege, bounded specialists, approval-required sensitive actions, budgets/circuit breakers.
  Owner: P03-B/P04-E.

- T011 HIGH — compromised model/provider exfiltrates sensitive context or returns manipulated action plans.
  Control direction: provider data-minimization, structured outputs, no secrets, independent deterministic controls, model/provider health and fallback without authority expansion.
  Owner: P03-C/P03-F/P04-B/P22-A.

- T012 HIGH — corrupted checkpoint/memory reintroduces stale authority, fabricated state or poisoned instructions.
  Control direction: integrity-protected checkpoints, minimal resumable state, revalidation of permissions/veto/fresh truth on resume.
  Owner: P03-E/P04-E/P22-G.

- T013 MEDIUM — unbounded token/tool loops create cost or availability exhaustion.
  Control direction: wall-clock/token/tool-call/cost/concurrency/retry budgets and circuit breakers.
  Owner: P04-E/P22-I.

### Market data / evidence integrity

- T014 CRITICAL — market-data poisoning/manipulated source feed drives unsafe decisions.
  Control direction: source authentication, cross-provider validation, provenance, quality confidence, quarantine, fail-closed downstream gating.
  Owner: P05/P07.

- T015 HIGH — stale/replayed data accepted as fresh.
  Control direction: event/source/receive timestamps, sequence/watermark checks, freshness policy, replay markers.
  Owner: P05/P07/P16.

- T016 HIGH — sequence gaps/duplicate/correction handling corrupts canonical state.
  Control direction: gap detection, deduplication, correction linkage, immutable/versioned raw evidence.
  Owner: P05/P06/P07.

- T017 HIGH — macro/news historical revision leakage creates look-ahead bias or false live context.
  Control direction: observed-at/vintage model, release-time gating, immutable revisions.
  Owner: P06/P10/P17.

- T018 HIGH — provenance or feature/model lineage tampering makes decisions unreproducible.
  Control direction: versioned manifests, hashes, signed/attested build and dataset references, append-only evidence.
  Owner: P06/P07/P17/P22.

### Risk / execution

- T019 CRITICAL — A5/A8 veto bypass via alternate code/tool/agent path.
  Control direction: architectural single path, deny-by-default gateway, code/policy checks, negative tests, independent audit.
  Owner: P03-E/P04-C/P16/P20.

- T020 CRITICAL — duplicate order caused by retry, timeout, idempotency collision or parallel route.
  Control direction: stable intent_id, route_attempt_id, provider client ID, one unresolved route, deterministic idempotency.
  Owner: P16/P20.

- T021 CRITICAL — blind cross-broker reroute while prior execution status is UNKNOWN.
  Control direction: halt, reconcile provider truth, recompute risk, fresh Firewall approval before new route.
  Owner: P20/P22.

- T022 CRITICAL — order/position/reconciliation state tampering hides real external exposure.
  Control direction: provider reconciliation, append-only lifecycle, mismatch quarantine, affected-scope execution halt.
  Owner: P20/P21/P22.

- T023 HIGH — stale RiskVerdict/FirewallVerdict replay authorizes execution after conditions change.
  Control direction: evaluated-at/valid-until, snapshot refs, expiry, fresh policy/data/account state checks.
  Owner: P15/P16/P20.

- T024 HIGH — precision/minimum/symbol/provider capability manipulation changes intended exposure.
  Control direction: canonical instrument contract, provider adapter validation, precision/minimum bounds, pre-submit contract checks.
  Owner: P05/P16/P20.

### Supply chain / CI / artifacts

- T025 CRITICAL — compromised dependency/build/plugin introduces hidden bypass or exfiltration.
  Control direction: dependency policy, lockfiles, SAST/CVE scanning, SBOM, provenance, review, pinned versions.
  Owner: P03-F/P04-B/P04-F.

- T026 CRITICAL — CI token/workflow compromise modifies protected source or release artifacts.
  Control direction: least-privilege workflow tokens, protected environments/branches, isolated trusted builders, review/attestation.
  Owner: P03-F/P04-C/P04-H.

- T027 HIGH — artifact/SBOM/provenance substitution between build and deployment.
  Control direction: content digest, signed artifacts/attestations, verify-before-promote, fail closed on mismatch.
  Owner: P04-F/P04-H/P24.

### Audit / observability / recovery

- T028 CRITICAL — audit/evidence tampering or deletion conceals unsafe action.
  Control direction: append-only/tamper-evident evidence, immutable manifests, access separation, integrity verification.
  Owner: P03-E/P22-A/P22-H/P24.

- T029 HIGH — telemetry suppression/blindness allows unsafe high-risk action without health/security truth.
  Control direction: mandatory critical telemetry, alert on gaps, fail closed beyond policy threshold.
  Owner: P03-E/P22-A/P22-J.

- T030 CRITICAL — malicious/corrupt backup or restore reintroduces compromised credentials/state/artifacts.
  Control direction: isolated backup domain, integrity manifests, restore quarantine, staged validation, credential revalidation, drills.
  Owner: P03-G/P22-E/P22-F/P22-G.

- T031 HIGH — destructive/ransomware event simultaneously affects primary and backup failure domain.
  Control direction: off-primary copies, independent credentials/failure domain, immutable/versioned backups where supported.
  Owner: P22-E/P22-G.

### Application / UX / notification surface

- T032 HIGH — public/application ingress exploit reaches privileged internal command surface.
  Control direction: strict authn/authz, input/schema validation, CSP/session controls, rate limiting, no direct execution/secrets connectivity.
  Owner: P03-B/P03-D/P23-G/P23-H.

- T033 MEDIUM — notification leaks sensitive execution/account/security data.
  Control direction: content classification, minimal notification payloads, channel trust policy, no secrets.
  Owner: P03-E/P23-F.

- T034 HIGH — denial-of-service on control/data/execution/security dependencies causes unsafe partial operation.
  Control direction: health states, circuit breakers, bounded queues, degraded/safe mode, dependency-specific fail-closed rules.
  Owner: P04/P05/P22.

- T035 HIGH — malicious insider/compromised endpoint performs high-risk config/policy/credential change without accountable review.
  Control direction: least privilege, step-up auth, maker/checker where required, signed/attributed changes, audit and rollback.
  Owner: P03-B/P03-C/P03-E/P24.

## 8. Trust-boundary coverage

Z0 ↔ Z1:
- T001, T002, T032, T034.

Z1 ↔ Z2:
- T002, T004, T008, T035.

Z2 ↔ Tool/Model/MCP:
- T008, T009, T010, T011, T012, T013.

Z2 ↔ Z3:
- T002, T014, T015, T018.

External Data ↔ Z3:
- T014, T015, T016, T017.

Z2/Z3 ↔ Z4:
- T019, T023, T024.

Z4 ↔ Broker/Exchange:
- T005, T006, T020, T021, T022, T024.

Z4 ↔ Z5:
- T003, T005, T006, T007.

All zones → Z6:
- T007, T028, T029.

Z6/Z3/Z4 ↔ Z7:
- T030, T031.

Source/CI/Registry → promoted artifacts:
- T025, T026, T027.

Every frozen G2 trust boundary has explicit analyzed threats.

## 9. Security-control ownership map

P03:
- threat model;
- RBAC/MFA/session/device;
- secret/KMS architecture;
- private administration;
- audit/change integrity;
- supply-chain security baseline;
- incident/emergency access;
- baseline security validation.

P04:
- concrete runtime/tool/dependency versions;
- CI security gates;
- SAST/CVE/SBOM/provenance;
- config/secret-reference contract;
- deterministic agent/tool evaluation harness;
- reproducible signed/attested artifacts.

P05–P07:
- source authenticity, sequence/freshness/gap controls;
- quality/provenance/quarantine.

P15–P16:
- deterministic Risk/Firewall controls and stale verdict rejection.

P20–P22:
- OMS idempotency/reconciliation;
- runtime diagnostics;
- incident response;
- backup/restore/DR drills.

P23:
- application/session/security UX;
- CSP/input/output controls;
- dangerous-action UX;
- notification data minimization.

P24:
- independent final security evidence before controlled production;
- production credential/account activation;
- Owner approval for Live progression.

## 10. Required validation scenarios downstream

P03/P04:
- stolen-session / revoked-session negative tests;
- RBAC deny matrix;
- Human Gate replay/scope-substitution test;
- secret redaction / leak drill;
- prompt-injection → forbidden tool test;
- malicious MCP/tool description/result test;
- A5/A8 veto bypass test;
- corrupted checkpoint resume test;
- dependency/build provenance substitution test.

P05/P07:
- stale/replayed/gapped/duplicated provider data;
- cross-provider divergence;
- source/provenance loss;
- quarantine propagation.

P16/P20:
- duplicate intent;
- timeout → UNKNOWN;
- cross-broker reroute attempt while UNKNOWN;
- stale Risk/Firewall verdict;
- account/provider mismatch;
- reconciliation mismatch.

P22:
- telemetry outage;
- audit sink unavailable;
- corrupted backup;
- compromised credential in restored state;
- failover and restore with required reconciliation.

## 11. Residual risk position

This P03-A artifact identifies risk; it does not claim mitigation completion.

Until P03-B through P03-H and later implementation phases complete:
- identity controls are architecture requirements, not production-proven controls;
- secrets/KMS product is not selected;
- security scanners are not installed by this task;
- runtime network/private-admin controls are not provisioned;
- no real account or execution credential exists;
- CANARY/LIVE remain disabled.

## 12. Reference lenses

Official/current reference lenses checked for this model:
- Microsoft Threat Modeling Tool / STRIDE guidance;
- NIST SP 800-218 Secure Software Development Framework v1.1 (final);
- NIST SP 800-218A GenAI/Dual-Use Foundation Model SSDF profile (final);
- OWASP GenAI Security Project Top 10, including Prompt Injection, Supply Chain, Data/Model Poisoning and Excessive Agency;
- MITRE ATLAS AI/agent adversarial technique knowledge base.

These references inform threat discovery only. NEXUS QUANT governance, FROZEN_G2 architecture, A5/A8 veto rules and Task Contracts remain authoritative.

## 13. Exit criteria for P03-A

P03-A is ready for implementation PR validation when:
- assets/security objectives are covered;
- all trust boundaries have analyzed threats;
- agent/LLM, market-data, execution, secrets, supply-chain and recovery threats are explicit;
- every HIGH/CRITICAL threat maps to a future control owner;
- security invariants are canonical;
- machine-readable register is valid JSON;
- diagrams match FROZEN_G2;
- no control is falsely claimed implemented;
- Governance Verify passes.

Canonical closure evidence is recorded in Current State. Any future semantic change to this baseline requires governed change control.

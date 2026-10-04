# NEXUS QUANT — Identity & Access Control Baseline

STATE = P03-B CANONICAL_BASELINE
TASK = `FIN-P03-WB-001`
LINEAR = `HOS-164`
BASELINE = `FROZEN_G2`
DATE = 2026-10-04

## 1. Purpose

Define the canonical authentication, authorization, session, device and identity-separation policy for NEXUS QUANT before runtime implementation.

This policy responds directly to P03-A threats T001–T013, T019, T025–T030, T032 and T035.

It does not provision an IdP, create credentials, implement application authentication or activate trading.

## 2. Core authorization equation

For every material action:

`effective_permission = task_scope ∩ principal_role ∩ agent_or_service_contract ∩ resource_scope ∩ environment_scope ∩ tool_policy ∩ current_security_state ∩ current_risk_state ∩ human_gate_when_required`

Any missing term means DENY.

Rules:
- deny by default;
- least privilege;
- no ambient administrator authority;
- permissions are action + resource + environment scoped;
- tool availability is not permission;
- no role may self-elevate;
- A5 Risk and A8 Security veto remain binding;
- Owner/Human Gate approval cannot suppress an active A5/A8 veto;
- country/location is not an authorization dependency or trusted authentication factor.

## 3. Principal classes

### H01 — Owner / Governance Human

Purpose:
- project governance;
- Human Gate approvals;
- policy/config approval;
- Global Halt / explicitly governed emergency actions.

Restrictions:
- cannot bypass Risk/Firewall/Security veto;
- cannot place arbitrary provider orders outside the canonical execution path;
- privileged actions require phishing-resistant MFA and step-up where classified sensitive.

### H02 — Security Operator

Purpose:
- security administration;
- session revocation;
- authenticator lifecycle;
- credential-revocation coordination;
- incident containment.

Restrictions:
- cannot raise risk ceilings;
- cannot originate trading signals;
- cannot bypass execution controls.

### H03 — Operations Operator

Purpose:
- health/incident/recovery operations;
- safe-mode/halt requests;
- diagnostics.

Restrictions:
- cannot silently change security or risk policy;
- cannot authorize new risk-increasing execution.

### H04 — Research Operator

Purpose:
- research, replay, analysis and model/evidence workflows.

Restrictions:
- no execution authority;
- no secrets administration;
- no production credential access.

### H05 — Auditor / Read-Only Reviewer

Purpose:
- read governed evidence, audit and policy state.

Restrictions:
- no operational mutation;
- no credential access beyond metadata explicitly required for audit.

### H06 — Future Execution Operator

State: DISABLED.

May only be activated by later governed tasks/gates. Its existence in the model grants no present authority.

## 4. Non-human principal classes

### M01 — Core Agent Identity

A0–A10 remain distinct logical principals.

Their permission is the intersection of:
- active Task Contract;
- canonical Agent Contract;
- Tool Gateway policy;
- environment;
- resource/action scope;
- A5/A8 veto;
- Human Gate where required.

Agent framework/model identity never expands canonical role authority.

### M02 — Specialist Agent Identity

Ephemeral and bounded by:
- parent authority;
- Specialist Contract;
- Task Contract;
- TTL/budgets;
- explicit tool/resource scope.

No ambient inheritance of all parent permissions.

### M03 — Domain Service / Workload Identity

One workload identity per bounded service/domain where feasible.

Requirements:
- machine-to-machine only;
- short-lived credentials/tokens preferred;
- audience/resource scoped;
- environment bound;
- not usable for human interactive login;
- no shared global service account.

### M04 — CI / Build Identity

Requirements:
- separate from runtime identity;
- repository/workflow/environment scoped;
- least-privilege token permissions;
- no production execution/account credential access;
- promotion authority separate from ordinary PR verification where later implemented.

### M05 — External Integration Identity

Provider/model/tool/MCP identities are integration principals, not project authorities.

External identity success does not grant NEXUS QUANT role authority.

## 5. Human RBAC matrix

Legend:
- A = allowed within governed scope;
- R = read only;
- G = requires Human Gate / step-up;
- D = denied;
- X = future disabled.

| Capability | Owner | Security | Ops | Research | Auditor | Future Execution |
|---|---:|---:|---:|---:|---:|---:|
| Read governed project state | A | A | A | A | R | X |
| Approve Human Gate | A | D | D | D | D | X |
| Change governance/security policy | G | G | D | D | R | X |
| Manage authenticators/sessions | G | A | D | D | R | X |
| Revoke credentials / security halt | G | A | G-request | D | R | X |
| Change risk ceilings | G-policy | D | D | D | R | X |
| Global Halt | A | G-security-halt | G-request | D | R | X |
| Research/replay | A | R | R | A | R | X |
| Read audit evidence | A | A | A | A-bounded | R | X |
| Mutate audit evidence | D | D | D | D | D | X |
| Direct broker/exchange order | D | D | D | D | D | X |
| Access raw secrets | D-by-default | D-by-default | D | D | D | X |

“Raw secrets” are resolved only by a secrets boundary for the exact workload/action; ordinary humans, agents and logs receive handles or metadata, not secret values.

## 6. Authentication baseline

### Privileged human access

Privileged human access MUST require MFA.

Preferred baseline:
- WebAuthn/FIDO public-key credential with user verification;
- platform passkey or hardware security key;
- at least one recovery-capable secondary authenticator enrolled before privileged production use.

For high-risk administrative access, phishing-resistant authentication is mandatory by policy.

Password-only privileged authentication is forbidden.

SMS/voice OTP:
- not accepted as the primary privileged MFA method;
- may not be the sole recovery path;
- any temporary compatibility use requires explicit risk acceptance and later removal.

TOTP:
- stronger than password-only but not phishing-resistant;
- permitted only as bounded fallback/recovery until phishing-resistant coverage is available;
- not sufficient alone for highest-risk administrative actions.

### Reauthentication / step-up

Fresh reauthentication is required for sensitive actions such as:
- adding/removing/resetting authenticators;
- changing recovery methods;
- granting/removing privileged roles;
- changing security policy;
- accessing or rotating execution credential handles;
- disabling security controls;
- changing Human Gate policy;
- enabling a higher environment;
- future CANARY/LIVE activation;
- emergency credential recovery;
- other actions marked HIGH/CRITICAL by policy.

A prior long-lived session is insufficient by itself.

## 7. Authenticator lifecycle and recovery

Enrollment:
- requires an authenticated session plus step-up for privileged accounts;
- new authenticator is bound to a stable principal ID;
- enrollment event is audited;
- existing authenticators are notified where supported.

Reset/recovery:
- never uses security questions;
- cannot rely only on email/SMS for privileged recovery;
- requires equivalent or stronger assurance than the action being recovered where feasible;
- may enter restricted recovery mode instead of immediately restoring full privilege;
- revokes or rotates affected sessions after successful recovery;
- produces a high-severity audit event.

Lost/compromised authenticator:
- can be revoked independently;
- all affected privileged sessions are revalidated or revoked;
- security incident path is available if compromise is suspected.

Break-glass:
- reserved for identity/security recovery, not trading convenience;
- time bounded;
- minimal privilege;
- separately audited;
- cannot bypass A5/A8 veto or grant LIVE trading authority.

## 8. Session policy

Session properties:
- server-verifiable, high-entropy session identifier/token;
- strict session issuance; unknown attacker-supplied session IDs are never adopted;
- transport only over TLS;
- browser session cookie uses Secure + HttpOnly and appropriate SameSite policy;
- session IDs do not appear in URLs;
- session state includes principal, assurance level, roles, environment, issue time, last activity and revocation state;
- privilege-changing events rotate the session identifier.

Session invalidation triggers:
- logout;
- password/authenticator reset;
- privileged role change;
- suspected compromise;
- security administrator revoke;
- account disable;
- major policy/assurance change;
- emergency security event.

Timeout policy:
- privileged sessions use shorter idle lifetime than normal read/research sessions;
- all authenticated sessions have absolute lifetime;
- reauthentication age for sensitive actions is stricter than general session lifetime;
- exact production durations are configured and tested in P23/P24, not assumed by this architecture task.

Concurrent sessions:
- must be visible/revocable to the account owner/admin;
- anomalous or policy-violating sessions may be terminated;
- concurrent-session limits are policy configurable.

## 9. Device policy

A device is a risk/context object, not an independent grant of authority.

Device state can include:
- device registration ID;
- authenticator binding;
- first/last seen timestamps;
- supported security capabilities;
- revocation state;
- compromise/risk flags.

Rules:
- a “trusted device” never bypasses required MFA for privileged access;
- new/unrecognized device can require step-up;
- compromised/revoked device fails closed for privileged actions;
- device trust expires/revalidates; it is not permanent;
- browser fingerprinting is minimized and is not an identity proof;
- country/location/geolocation is not required, inferred as identity, or trusted as authorization proof.

## 10. Authorization semantics

Every authorization decision evaluates:
- principal ID and class;
- authenticated assurance;
- role/capability;
- action;
- resource;
- environment;
- task/lock/gate;
- current A8 Security state;
- current A5 Risk state for financial paths;
- Human Gate binding when required;
- session freshness;
- device/security flags where applicable.

High-risk authorization records:
- decision ID;
- principal;
- normalized action;
- resource/environment;
- policy version;
- assurance level;
- Human Gate reference if used;
- allow/deny reason;
- evaluated-at/expiry where applicable;
- correlation/audit ID.

## 11. Environment isolation

DEV / TEST / RESEARCH / DEMO / SHADOW / CANARY / LIVE are separate authority contexts.

Rules:
- lower-environment identity cannot write higher-environment authoritative state;
- credentials/tokens are environment bound;
- SHADOW cannot obtain live command authority;
- a principal authenticated in one environment does not automatically gain another environment;
- promotion of code/model/config does not promote human/agent/session authority;
- CANARY/LIVE identities remain disabled until later gates.

## 12. Human Gate anti-replay

Approval must bind:
- approval ID;
- task/run/principal;
- exact action;
- normalized argument digest;
- resource;
- environment;
- evidence references;
- expiry;
- one-use/replay state.

Any material argument/resource/environment change requires a new approval.

Approval does not survive:
- expiry;
- task/lock invalidation;
- active A5/A8 veto;
- principal/session revocation;
- material security-context change.

## 13. Service-to-service policy

Service/workload authentication must:
- use distinct non-human identity;
- avoid shared static human passwords;
- prefer short-lived, audience-bound credentials;
- validate issuer/audience/resource/environment;
- be rotated/revocable;
- be auditable;
- never grant more than the receiving API action requires.

Direct database ownership crossing remains forbidden even when authentication succeeds.

## 14. Audit events

At minimum, record:
- login success/failure;
- MFA enrollment/removal/reset;
- recovery flow start/complete/failure;
- role grant/revoke;
- session create/rotate/revoke;
- step-up success/failure;
- device register/revoke/risk-state change;
- authorization denial for sensitive action;
- Human Gate create/approve/deny/expire/replay rejection;
- service/workload credential issue/revoke;
- privileged policy change;
- break-glass activation/termination.

Never log raw password, authenticator secret, private key, API key or full session secret.

## 15. Negative authorization invariants

The following MUST remain denied:
- Strategy/Signal/UX/Research directly submitting broker orders;
- A0 overriding A5 or A8;
- agent/tool role self-elevation;
- Security role raising risk ceilings;
- Operations silently changing risk/security policy;
- lower environment writing CANARY/LIVE;
- trusted-device status bypassing privileged MFA;
- recovery flow silently restoring stronger privilege than verified;
- external IdP/MCP/model identity being treated as internal authorization;
- raw secrets exposed to ordinary agent/model context;
- audit record mutation to erase prior decisions.

## 16. Downstream implementation ownership

P03-C:
- secret/KMS/vault architecture and credential lifecycle.

P03-D:
- private admin exposure/network access controls.

P03-E:
- audit integrity and high-risk change enforcement.

P03-G:
- incident/emergency access and recovery.

P04:
- concrete authn/authz libraries, service identity mechanism, policy engine integration and CI tests.

P23:
- web/mobile login, WebAuthn/passkey UX, cookie/session controls, account security UI.

P24:
- final production identity assurance, CANARY/LIVE activation evidence and Owner gate.

## 17. Current implementation state

Identity provider: NOT_SELECTED  
Authentication runtime: NOT_IMPLEMENTED  
WebAuthn runtime: NOT_IMPLEMENTED  
Production users/accounts: NONE  
Production secrets: NONE  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This artifact defines policy; it does not claim the controls are deployed.

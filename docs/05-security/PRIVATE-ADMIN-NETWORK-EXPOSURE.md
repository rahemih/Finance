# NEXUS QUANT — Private Administration & Network Exposure Baseline

STATE = P03-D CANONICAL_BASELINE
TASK = `FIN-P03-WD-001`
LINEAR = `HOS-166`
BASELINE = `FROZEN_G2`
DATE = 2026-10-04

## 1. Purpose

Define how NEXUS QUANT exposes user-facing, internal, privileged-administration, execution, secrets, observability and recovery resources before any network product or infrastructure is selected.

This policy refines the frozen Z0–Z7 topology without changing it.

No firewall, VPN, ZTNA, bastion, proxy, WAF, VPC/VNet or service mesh is provisioned by P03-D.

## 2. Zero-trust rule

Network location is context, not authorization.

The following do **not** grant trust by themselves:
- private IP;
- LAN membership;
- VPN membership;
- office/home network;
- cloud subnet;
- device ownership;
- country or geolocation.

Every privileged access decision must bind:
- principal identity;
- P03-B assurance/MFA state;
- role/capability;
- session freshness;
- device/security state where applicable;
- resource;
- action;
- environment;
- current A8 security state;
- Human Gate when required.

## 3. Exposure classes

### E0 — Public Edge

Purpose:
- public website/UI entry;
- explicitly public documentation/assets;
- tightly bounded public API surface where later authorized.

Controls direction:
- TLS only;
- strict routing;
- rate limits/abuse controls;
- DDoS protection class;
- WAF/API-gateway policy where justified;
- schema/input validation downstream;
- no admin endpoint;
- no secrets;
- no direct data-store/execution access.

### E1 — Authenticated Application Ingress

Purpose:
- authenticated owner/team application/API access.

Controls direction:
- P03-B authn/authz/session policy;
- resource/action scoped;
- read models/domain APIs only;
- cannot expose broker order endpoints or secret-resolution endpoints directly.

### E2 — Private Administrative Access

Purpose:
- privileged governance/security/operations administration.

Controls direction:
- identity-aware access proxy / ZTNA / VPN+bastion class patterns may be evaluated later;
- network membership alone never suffices;
- phishing-resistant privileged MFA;
- device/security posture policy where supported;
- just-in-time/time-bounded elevation preferred;
- admin interfaces not exposed on ordinary public ingress;
- full audit/session attribution;
- emergency access separately governed.

### E3 — Internal Service Access

Purpose:
- service-to-service domain traffic.

Controls direction:
- default deny;
- workload identity;
- exact service/API/resource policy;
- environment bound;
- mTLS/service identity class where later selected;
- no broad flat-network trust.

### E4 — Controlled External Egress

Purpose:
- market/macro/news/on-chain providers;
- model/tool/MCP services;
- future broker/exchange endpoints;
- approved notification services.

Controls direction:
- destination/service class policy;
- DNS/TLS identity validation;
- proxy/egress gateway class where justified;
- explicit provider/broker adapter ownership;
- deny unknown/unnecessary destinations;
- sensitive routes audited;
- broker order egress only from Z4.

### E5 — Restricted Execution Access

Purpose:
- Z4 Risk/Firewall/OMS/adapters/reconciliation.

Rules:
- no public inbound path;
- no direct user/browser/agent-text path;
- accepts only validated internal execution contracts;
- broker/exchange order egress originates only here;
- admin access is exceptional, privileged, audited and cannot bypass A5/A8/Firewall.

### E6 — Restricted Security/Secrets Access

Purpose:
- Z5 identity/security/secrets.

Rules:
- no public raw-secret endpoint;
- secret resolution only for explicitly authorized workload identities/handles;
- human plaintext secret access remains exceptional under P03-C;
- security admin path uses E2 controls;
- no bulk/ambient secret access.

### E7 — Observability / Audit Access

Purpose:
- Z6 logs/metrics/traces/evidence/security events.

Rules:
- ingest does not grant control-plane/business authority;
- read access role scoped;
- administrative mutation tightly limited;
- no public direct write/query surface unless explicitly mediated;
- sensitive data redacted under P03-C.

### E8 — Backup / DR Access

Purpose:
- Z7 backup, restore manifests, recovery staging.

Rules:
- no public inbound path;
- separate recovery authorization;
- privileged access with P03-B controls;
- restore does not grant execution authority;
- recovery paths audited and integrity checked.

## 4. Trust-zone exposure matrix

| Zone | Internet inbound | User/app inbound | Admin inbound | Internal service | External egress | Notes |
|---|---|---|---|---|---|---|
| Z0 User Edge | N/A | N/A | N/A | N/A | E0/E1 only | client context |
| Z1 App Ingress | E0/E1 only | Allowed via controlled ingress | No ordinary admin plane | To authorized domain APIs | Limited | no broker/secrets direct |
| Z2 Control Plane | DENY | Via authorized internal APIs only | E2 | E3 | E4 via policy | no direct public exposure |
| Z3 Data Plane | DENY | No direct access | E2 exceptional | E3 | E4 to data providers | cannot execute orders |
| Z4 Execution Enclave | DENY | DENY | E2 exceptional | E3 validated contracts | E4 broker/exchange only | most restricted app zone |
| Z5 Security/Secrets | DENY | DENY | E2 restricted | E3 exact workload only | minimal/required | no bulk secret access |
| Z6 Observability/Audit | DENY by default | mediated read views only | E2 | telemetry ingest E3 | controlled integrations | no business authority |
| Z7 Backup/DR | DENY | DENY | E2 recovery-only | controlled recovery path | minimal | separate recovery controls |

## 5. Administrative entry-point policy

Production-capable administration, when later enabled, must converge on a small number of governed entry points rather than exposing native admin ports broadly.

Permitted future patterns to evaluate:
- identity-aware proxy / ZTNA;
- VPN combined with identity-aware authorization;
- bastion/jump host with short-lived access;
- managed session broker;
- privileged access management class.

No pattern is trusted merely because it creates a private tunnel.

Administrative access requires:
1. authenticated privileged principal;
2. phishing-resistant MFA;
3. valid session and role;
4. device/security context if policy requires;
5. exact environment/resource/action authorization;
6. time-bound elevation for high-risk actions where feasible;
7. audit/evidence;
8. A8 veto and Human Gate where applicable.

## 6. Management-plane separation

The management plane is distinct from user/application traffic.

Rules:
- admin UI/API is not mounted under the normal public user route merely behind a hidden URL;
- management listener/path has independent authorization policy;
- native database/cache/queue/KMS/host admin ports are not internet exposed;
- control-plane administration does not use execution-provider order interfaces as a shortcut;
- diagnostics endpoints are private or strongly mediated and never expose secrets;
- health endpoints disclose minimum necessary information.

## 7. East-west service policy

Default posture: DENY unless explicitly required.

An internal request must be attributable to:
- source workload/service identity;
- destination service/API;
- environment;
- allowed action;
- policy version.

Examples:
- Z2 may call authorized domain APIs;
- Z3 may publish canonical/quality events but not call broker order endpoints;
- Z4 may resolve exact S5 secret handles through Z5 but not enumerate all secrets;
- Z6 accepts telemetry but cannot mutate business state merely because it received traffic;
- Z7 restore staging cannot submit new orders.

IP/subnet membership alone is insufficient.

## 8. Egress policy

### Data / macro / news / on-chain
Only designated adapters fetch approved sources.
Inbound content remains untrusted data.

### Model / tool / MCP
Only through the Tool Gateway or governed integration boundary.
Remote tool reachability does not grant authority.

### Broker / exchange
- order traffic only from Z4;
- market/status/reconciliation endpoints accessed by appropriate Z4 adapters;
- no direct browser/agent/research egress for order submission;
- destination/provider identity and TLS validation required;
- egress failure or ambiguous provider response follows UNKNOWN/reconciliation rules.

### Notifications
Only sanitized/minimum necessary data.
Never transport raw secrets.

## 9. Public ingress controls direction

When public application ingress exists, the implementation baseline should include as appropriate:
- TLS termination with modern policy;
- DDoS protection class;
- rate limiting and abuse throttling;
- WAF/API schema enforcement;
- request-size/time/concurrency bounds;
- bot/automation controls where justified;
- authentication boundary;
- CSP/cookie/header controls in P23;
- safe error responses;
- observability without sensitive leakage.

These controls supplement, not replace, application authorization.

## 10. Administrative device policy

P03-B applies fully.

Additional network/access requirements:
- compromised/revoked device cannot retain privileged administrative reach;
- trusted-device status never bypasses phishing-resistant MFA;
- admin access from unmanaged device may be denied or restricted;
- device posture signals are inputs, not sole authorization;
- no policy assumes geographic location proves legitimacy.

## 11. Just-in-time privilege and standing access

Direction:
- minimize standing privileged network reach;
- prefer time-bounded/JIT access for sensitive admin planes;
- revoke route/session when task/window ends;
- separate read/observe access from mutation access;
- production-capable access requires stronger evidence than lower environments.

Permanent broad allowlists for personal IPs are not a canonical security control.

## 12. Break-glass / emergency network access

Emergency network access:
- is recovery/containment only;
- cannot grant trading bypass;
- remains bounded to exact environment/resource;
- requires strong authentication where technically possible;
- is time-limited;
- creates high-severity audit evidence;
- must be revoked/reviewed after incident;
- cannot silently become the normal admin path.

If identity infrastructure is impaired, recovery access must still preserve a separate accountable identity/evidence trail rather than a shared anonymous credential.

## 13. Exposure-specific fail-closed rules

Fail closed for privileged mutation when:
- identity/role cannot be verified;
- MFA/session assurance is insufficient;
- device is revoked/compromised under policy;
- target environment/resource mismatches authorization;
- A8 security state blocks action;
- required audit path is unavailable beyond policy tolerance;
- destination/provider identity is uncertain for sensitive egress;
- network path unexpectedly exposes Z4/Z5/Z7 publicly;
- policy evaluation is unavailable for HIGH/CRITICAL admin action.

Availability degradation may preserve read-only diagnostics while blocking privileged mutation.

## 14. Logging and evidence

Administrative access evidence includes:
- principal;
- device/session reference;
- source connection metadata as context;
- entry point;
- target zone/resource;
- environment;
- action;
- authorization result;
- step-up/Human Gate reference where required;
- start/end/revocation;
- policy version;
- correlation ID.

Do not treat source IP/location as identity.

## 15. Network data minimization

Network/security telemetry may record connection metadata required for defense and audit, but:
- do not expose secrets/tokens;
- minimize personal/device fingerprint data;
- define retention later under P22/P23 policy;
- country/location analytics must not become project authorization assumptions.

## 16. Downstream implementation ownership

P04:
- concrete gateway/proxy/network/runtime/security technology selection;
- configuration as code and CI validation;
- network policy tests.

P22:
- runtime diagnostics, incident response, network observability, failover/recovery.

P23:
- public application ingress, CSP/session/security headers, frontend/API exposure.

P24:
- production exposure review;
- CANARY/LIVE admin-path verification;
- independent security evidence before activation.

## 17. Required downstream validation

- internet scan shows only intended public endpoints;
- admin plane is unreachable through ordinary public ingress;
- Z4/Z5/Z7 have no public inbound route;
- private/VPN-only connection without valid identity is denied;
- valid identity with wrong environment/resource is denied;
- compromised/revoked device privileged access is denied;
- lower environment cannot reach higher admin/data planes;
- research/data plane cannot reach broker order path;
- execution broker egress originates only from Z4;
- unknown egress destination is denied;
- break-glass use is logged and expires;
- public ingress rate-limit/DDoS/WAF controls are tested when implemented.

## 18. Current implementation state

ZTNA/VPN/bastion: NOT_SELECTED / NOT_PROVISIONED  
Firewall/security groups: NOT_PROVISIONED_BY_THIS_TASK  
WAF/API gateway: NOT_SELECTED / NOT_PROVISIONED  
Service mesh: NOT_SELECTED / NOT_PROVISIONED  
Production network endpoints: NONE AUTHORIZED BY P03-D  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This is a policy baseline only.

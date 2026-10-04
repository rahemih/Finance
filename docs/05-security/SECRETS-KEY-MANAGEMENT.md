# NEXUS QUANT — Secrets & Key Management Baseline

STATE = P03-C IMPLEMENTATION
TASK = `FIN-P03-WC-001`
LINEAR = `HOS-165`
BASELINE = `FROZEN_G2`

## 1. Security position

NEXUS QUANT uses a secret-reference model: application, agent and workflow configuration stores references/handles, not raw secret values.

Canonical direction:
- centralized secret-manager/vault class for secret objects;
- KMS/HSM-backed key management class for cryptographic keys/trust anchors where appropriate;
- workload identity and short-lived/dynamic credentials preferred over static shared secrets;
- environment, domain and resource separation;
- least privilege, auditable access, rotation/revocation and fail-closed compromise handling.

No vendor is selected or provisioned by P03-C.

## 2. Secret classes

| Class | Examples | Sensitivity | Key rule |
|---|---|---:|---|
| S0 | public endpoint/config | PUBLIC | not a secret; integrity still matters |
| S1 | service/workload credential | HIGH | short-lived/dynamic preferred |
| S2 | market/macro/data provider API key | HIGH | provider/domain/env scoped |
| S3 | model/tool/MCP provider credential | HIGH | no prompt/log exposure |
| S4 | DB/cache/storage credential | HIGH | workload/env scoped; dynamic preferred |
| S5 | broker/exchange execution credential | CRITICAL | trading-only; no withdrawal/transfer where separable |
| S6 | signing/provenance key | CRITICAL | protected key service/HSM-class boundary preferred |
| S7 | auth/session/certificate private material | CRITICAL | never exposed to ordinary application/log context |
| S8 | backup encryption/recovery key | CRITICAL | separate recovery trust/failure domain |

## 3. Secret handle contract

Conceptual reference:

`secret://<environment>/<domain>/<name>@<version-or-alias>`

A reference may carry:
- secret class;
- owner domain;
- environment;
- intended consumer identity;
- provider/resource;
- allowed operation;
- rotation/revocation metadata.

It MUST NOT contain the secret value.

Raw values are forbidden in:
- Git commits/history;
- Linear issues/documents;
- model/agent prompts or memory;
- ordinary application logs/traces;
- telemetry attributes;
- support screenshots/dumps;
- task contracts/evidence artifacts.

## 4. Environment isolation

DEV, TEST, RESEARCH, DEMO, SHADOW, CANARY and LIVE use separate credential authority.

Rules:
- no credential is automatically reused across environments;
- lower environments cannot read/decrypt CANARY/LIVE secrets;
- KMS/vault namespaces and access policies are environment-scoped;
- CANARY/LIVE credentials do not exist until later governed gates;
- SHADOW has no live execution credential;
- promotion of code/config never promotes secret material;
- production compromise cannot be “fixed” by copying a lower-environment secret.

## 5. Key hierarchy / envelope encryption

Logical direction:
1. trust/root key material remains inside a controlled key-management boundary;
2. Key Encryption Keys are separated by environment and cryptographic purpose;
3. Data Encryption Keys protect eligible application/data objects;
4. encrypted data stores ciphertext plus key/version metadata, never the plaintext KEK;
5. rotation supports versioning and controlled decrypt-old/encrypt-new transition.

No root/KEK private material is exposed to agents or ordinary application configuration.

Key purpose separation is mandatory: encryption, signing, authentication and backup/recovery keys are not interchangeable.

## 6. Lifecycle

Each secret/key has:
- owner;
- class/purpose;
- environment;
- consumers;
- created/issued time;
- version;
- rotation policy;
- expiry where applicable;
- revocation method;
- last rotation/review evidence.

Lifecycle:
CREATE / ISSUE → ACTIVE → ROTATING → REVOKED / EXPIRED → DESTROYED_OR_ARCHIVED_AS_POLICY_REQUIRES.

Dynamic secrets:
- preferred where supported;
- issued for bounded workload/session lifetime;
- automatically expire/revoke.

Static secrets:
- exceptional/compatibility use;
- unique per environment/consumer where feasible;
- automated or governed rotation;
- immediate rotate/revoke after suspected exposure.

User passwords are not rotated on arbitrary schedules; credential changes follow the P03-B identity policy and compromise evidence.

## 7. Future execution credentials

S5 is the highest operational secret class.

Future broker/exchange credentials MUST:
- be bound to the execution enclave/workload;
- be environment/account/provider scoped;
- request only required trading permissions;
- disable/omit withdrawal, transfer and unrelated account-management permissions where provider controls allow;
- never be available to Strategy/Signal/Research/UX/model context;
- be represented outside the secrets boundary only by an opaque handle;
- support rapid revoke/rotate;
- be revalidated after restore/failover/incident;
- remain nonexistent while LIVE is disabled.

Unknown credential integrity => halt affected execution scope.

## 8. Human access

Default human access to raw values = DENY.

Humans may manage metadata/policy without reading values when the platform supports it.

Exceptional plaintext access requires:
- explicit high-risk authorization;
- phishing-resistant privileged authentication;
- exact secret/resource scope;
- reason/ticket/evidence;
- time-bounded access;
- audit;
- no copying into unmanaged channels.

Owner authority does not imply bulk raw-secret visibility.

## 9. Agent / LLM boundary

Agents/models:
- receive secret handles or capability-scoped tools;
- never receive reusable raw production credentials in prompts;
- cannot enumerate all secrets;
- cannot request a secret outside Task/Agent/Tool policy;
- cannot persist secret values to memory/checkpoints/evidence;
- fail closed if a tool result unexpectedly contains a secret-class value;
- trigger redaction/quarantine/incident handling on suspected leak.

A8 may veto/revoke. A0 cannot override A8.

## 10. CI/CD

CI identity is separate from runtime identity.

Direction:
- prefer short-lived federation/workload identity to static cloud/runtime credentials where supported;
- PR/untrusted/fork workflows receive no sensitive production secrets;
- workflow token permissions are minimal;
- environment promotion uses protected environments/policies;
- build/test jobs do not receive broker/exchange credentials;
- secret scanning and push protection remain defense-in-depth, not a substitute for vaulting;
- logs mask/redact secret values.

## 11. Rotation and zero/low-downtime change

Rotation plan depends on secret type:
- create new version;
- grant intended consumer;
- switch new reads/writes/use;
- verify;
- revoke old version;
- monitor rejected old-version usage.

For encryption keys, re-encryption may be gradual; key metadata must preserve ability to decrypt authorized historical ciphertext until policy permits retirement.

Compromise rotation is immediate and may intentionally interrupt service rather than operate with uncertain credentials.

## 12. Audit

Audit at minimum:
- secret/key create/import;
- policy grant/revoke;
- read/resolve/use where available;
- failed/denied access;
- rotation;
- revocation;
- deletion/destruction;
- export attempt;
- key-sign/decrypt operation for critical keys where platform supports;
- emergency access;
- secret scanning detection;
- restore/recovery key use.

Audit records contain identity/handle/version/action/result, never raw secret values.

## 13. Backup / recovery

Rules:
- backup data encryption keys/recovery material follow explicit cryptographic recovery policy;
- execution/provider credentials are not blindly restored from stale backup into active authority;
- restored secret metadata is quarantined until identity, policy, key integrity and external provider state are revalidated;
- loss/uncertainty of critical key material can require fail-closed data or execution scope;
- recovery trust material is isolated from the same failure domain where practical;
- restoration of secrets never implies restoration of CANARY/LIVE authorization.

## 14. Incident response

Suspected leak:
1. classify secret and blast radius;
2. halt affected privileged/execution path when required;
3. revoke/disable exposed credential;
4. issue replacement through governed path;
5. invalidate dependent sessions/tokens if relevant;
6. inspect logs/audit for use;
7. remove exposed plaintext from active surfaces while preserving forensic integrity;
8. document cause and prevention;
9. verify old credential rejection before normal operation resumes.

## 15. Candidate implementation patterns deferred to P04+

Permitted future implementations may include:
- cloud secret-manager + KMS;
- self-managed vault-class service;
- HSM-backed signing/KMS for high-value keys;
- workload-identity federation;
- SPIFFE/SVID-class service identity where it fits the selected runtime.

P03-C chooses the security contract, not the vendor.

## 16. Required downstream tests

- repository/CI secret-leak tests;
- forbidden raw-secret serialization/log tests;
- cross-environment access denial;
- wrong-workload/wrong-audience secret denial;
- revoked/expired secret rejection;
- rotation overlap and old-version rejection;
- compromised-secret emergency rotation;
- agent prompt/tool leak quarantine;
- broker credential no-withdrawal permission validation before any activation;
- backup/restore credential quarantine test.

## 17. Current state

Vault/secret manager: NOT_SELECTED / NOT_PROVISIONED  
KMS/HSM: NOT_SELECTED / NOT_PROVISIONED  
Real API keys: NONE  
Broker/exchange accounts/credentials: NONE  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This is a policy baseline only.

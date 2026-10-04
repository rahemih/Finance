# NEXUS QUANT — Security Tooling Baseline

STATE = GOVERNED_COMPANION  
TASK = `FIN-P01-WS-001`  
LINEAR = `HOS-152`

## 1. Security authority

A8 Security is the independent security authority for NEXUS QUANT.

Security tools:
- detect;
- prevent;
- validate;
- produce evidence;
- enforce deterministic controls where configured.

They do not grant authority and cannot bypass:
- Task Contracts;
- locks;
- A5 Risk veto;
- A8 Security veto;
- Human Gates.

## 2. Defense-in-depth layers

The project security model must cover:

1. source control;
2. secrets;
3. static analysis;
4. dependencies and CVEs;
5. SBOM and software inventory;
6. build provenance and artifact integrity;
7. policy-as-code;
8. API/web attack surface;
9. agent/LLM prompt and tool abuse;
10. runtime threat detection;
11. operational incident evidence and recovery.

## 3. Source and secret controls

Baseline:
- GitHub Secret Protection and Push Protection remain enabled;
- credentials are never committed;
- secrets never enter ordinary Linear descriptions, prompts, logs or evidence comments;
- examples/tests use non-sensitive fixtures;
- exposed credentials are treated as compromised and revoked/rotated.

## 4. Static analysis

Preferred direction:
- CodeQL = primary governed SAST candidate;
- Semgrep = custom NEXUS rule layer where CodeQL does not express the project-specific invariant efficiently.

Project-specific rules should eventually cover:
- forbidden direct execution paths;
- missing A5/A8 gate checks;
- credential misuse;
- permissive security defaults;
- unsafe shell/process execution;
- unsafe deserialization;
- prompt/tool trust-boundary violations;
- missing authorization/idempotency in sensitive actions.

## 5. Dependency, CVE and misconfiguration scanning

Preferred direction:
- Trivy = broad primary candidate for repository/image/dependency/misconfiguration coverage;
- Grype = optional independent vulnerability validation against SBOM/image evidence.

Do not run redundant scanners without a measured reason.

## 6. SBOM

Preferred direction:
- Syft for explicit SBOM generation;
- CycloneDX as the canonical interchange family;
- release process stores SBOM with artifact/evidence.

Missing or invalid required SBOM becomes a release blocker once P04 enables the control.

## 7. Signing and provenance

Preferred direction:
- Cosign for artifact/container signing;
- SLSA-class provenance for build evidence.

Before activation P04 must define signing identity/key model, verification policy, trusted builders, attestation storage and rollback.

Signature or provenance mismatch fails closed.

## 8. Policy-as-code

OPA is the preferred candidate for centralized deterministic policy where it materially improves security/governance.

Candidate policy classes:
- tool permission;
- environment access;
- deployment authorization;
- sensitive workflow eligibility;
- agent capability checks;
- risk/security preconditions;
- artifact/release rules.

OPA cannot increase its own permission set or override Human Gate boundaries.

## 9. Secrets and key management

P03 must select one primary governed secrets/KMS architecture.

Candidate direction:
- cloud-native Secret Manager/KMS where infrastructure choice makes this simplest;
- Vault-class solution only if its operational value justifies the additional burden.

Required properties:
- least privilege;
- environment separation;
- rotation;
- auditability;
- emergency revoke;
- no withdrawal permission by default;
- no raw secret values in model context.

## 10. DAST / API / web security

OWASP ZAP is the preferred open-source DAST/API candidate.

Rules:
- active scans only against explicitly authorized environments;
- never scan a third-party or production target merely because a URL is known;
- OpenAPI/API definitions should be reused for coverage;
- authentication/session/CSP/cookie/header findings become P23/P24 evidence.

## 11. Agent / LLM security

Promptfoo, Inspect AI and the project-native evaluation harness are candidates for:
- prompt injection;
- malicious tool requests;
- external-content instruction attacks;
- privilege escalation;
- forbidden action requests;
- schema bypass;
- stale/conflicting source manipulation;
- model/provider outage;
- false confidence;
- veto bypass attempts.

External web/email/PDF/news/repository content is untrusted data, not policy instruction.

## 12. Runtime security

Falco is conditional.

Evaluate in P22 only if selected runtime topology makes syscall/container runtime detection materially useful.

Runtime security also depends on:
- least privilege;
- network segmentation;
- secret isolation;
- immutable/reproducible artifacts;
- observability;
- circuit breakers;
- incident response.

## 13. Security CI gate model

After P03/P04 selection:

```text
PR / source
  -> secret protection
  -> SAST
  -> custom policy/rules
  -> vulnerability / dependency / misconfiguration scan
  -> SBOM
  -> build
  -> provenance / signing
  -> authorized test deployment
  -> DAST / runtime tests
  -> A8 review/evidence gate
  -> release eligibility
```

## 14. Severity / exception direction

P03/P04 sets exact thresholds.

Default direction:
- Critical unresolved issue -> block;
- confirmed secret exposure -> revoke/rotate and block;
- signature/provenance mismatch -> block;
- security control unavailable for a sensitive action -> fail closed;
- A8 veto -> STOP;
- exception -> explicit evidence, owner, expiry and compensating controls.

## 15. Observability and evidence

Security events should eventually carry:
- task_id;
- run_id;
- source/tool;
- rule/query ID;
- asset/path/artifact;
- severity;
- finding fingerprint;
- first/last seen;
- fix/exception state;
- evidence links;
- related incident;
- remediation version/commit.

A10 preserves audit evidence. A8 owns security disposition.

## 16. Phase activation

- P01: registry/readiness only.
- P03: architecture and security tool selection.
- P04: CI/build/release enforcement.
- P22: runtime/operations/incident controls.
- P23: application/UX attack-surface validation.
- P24: final independent security verification and production-gate evidence.

No production scanner/runtime is installed by this baseline.

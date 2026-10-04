# Finance / NEXUS QUANT — Security Tooling Registry

STATE = GOVERNED_SECURITY_REGISTRY  
TASK = `FIN-P01-WS-001`  
LINEAR = `HOS-152`  
EFFECTIVE_DATE = 2026-10-04  
PRODUCTION_INSTALLATION = NOT_AUTHORIZED_BY_THIS_REGISTRY

## 1. Purpose

This registry defines the security tooling candidates and defense-in-depth responsibilities for NEXUS QUANT.

It is a readiness and selection baseline, not an instruction to install every scanner now.

The target coverage is:

```text
Source
  -> SAST
  -> Secrets
  -> Dependencies / CVEs
  -> SBOM
  -> Build Provenance / Signing
  -> API / Web Security
  -> Agent / LLM Security
  -> Runtime Security
  -> Incident / Evidence
```

A8 Security is the canonical security authority. Tools provide evidence and enforcement primitives; they do not replace A8 authority.

## 2. Preferred layered stack

| Layer | Primary direction | Secondary / conditional |
|---|---|---|
| Repository secret defense | GitHub Secret Protection / Push Protection | Trivy secret scan / later dedicated secondary scanner if justified |
| SAST | GitHub CodeQL | Semgrep for project-specific rules |
| Dependency / image / repo CVE scan | Trivy | Grype for SBOM-centric independent scan |
| SBOM | Syft + CycloneDX | tool-specific native SBOM output |
| Policy-as-code | OPA | repository-native deterministic gates |
| Artifact signing | Cosign | selected platform signing integration |
| Build provenance | SLSA-class provenance | platform-native attestations |
| Secrets/KMS | selected cloud Secret Manager/KMS or governed Vault-class solution | none by default |
| DAST/API | OWASP ZAP | additional commercial DAST only if justified |
| Agent/LLM security | Promptfoo + Inspect AI | project-native red-team harness |
| Runtime detection | Falco | only if Linux/container/Kubernetes topology makes it useful |
| Security evidence | A10 evidence + CI/security artifacts | selected SIEM/observability backend later |

## 3. Candidate registry

Upstream GitHub metadata observed on 2026-10-04.

| Tool | Security role | License signal | Classification | Main roadmap use | Guardrail |
|---|---|---|---|---|---|
| GitHub Secret Protection / Push Protection | secret prevention | platform capability | ACTIVE_NOW | P00+ / P03 / P04 | do not weaken protections |
| GitHub CodeQL / `github/codeql` | SAST / code scanning | repo metadata MIT; platform applicability must be rechecked | ADOPT_CANDIDATE | P03 / P04 / P24 | CI gate after language/runtime selection |
| `aquasecurity/trivy` | vulnerabilities, misconfigurations, secrets, SBOM | Apache-2.0 | ADOPT_CANDIDATE | P03 / P04 / P22 / P24 | avoid duplicating every function with extra scanners |
| `semgrep/semgrep` | pattern-based SAST / custom security rules | LGPL-2.1 | USE_CANDIDATE + LICENSE_REVIEW | P03 / P04 | use mainly for NEXUS-specific rules not covered well by CodeQL |
| `zaproxy/zaproxy` | DAST / API / web application testing | Apache-2.0 | ADOPT_CANDIDATE_FOR_DAST | P23 / P24 | active scanning only against explicitly authorized environments |
| `falcosecurity/falco` | runtime threat detection | Apache-2.0 | CONDITIONAL | P22 / P24 | evaluate only if runtime topology justifies runtime monitoring |
| `anchore/grype` | vulnerability scan of images/filesystems/SBOMs | Apache-2.0 | ALTERNATIVE / INDEPENDENT_CHECK | P03 / P04 / P24 | do not run beside Trivy by default unless independent evidence is useful |
| `anchore/syft` | SBOM generation | Apache-2.0 | ADOPT_CANDIDATE | P03 / P04 / P24 | pin version and validate SBOM completeness |
| `CycloneDX/cyclonedx-cli` | SBOM merge/diff/convert/analyze | Apache-2.0 | ADOPT_CANDIDATE | P03 / P04 / P24 | format/process tooling, not vulnerability authority by itself |
| `sigstore/cosign` | artifact/container signing | Apache-2.0 | ADOPT_CANDIDATE | P04 / P24 | signing identity/key policy must be defined before use |
| SLSA-class provenance | build provenance / attestations | standard | BASELINE_STANDARD | P04 / P24 | provenance must bind artifact to trusted build evidence |
| `open-policy-agent/opa` | policy-as-code | Apache-2.0 | ADOPT_CANDIDATE | P03 / P04 / P15 / P16 / P24 | policy engine cannot auto-expand authority |
| selected cloud KMS/Secret Manager or Vault-class solution | secrets/key lifecycle | exact product terms later | ADOPT_CANDIDATE | P03 / P04 | no secret values in source, Linear, prompts or ordinary logs |
| Codex Security | assisted security review | service capability | ACTIVE_NOW | P03 / P04 / P24 | findings require canonical repo evidence |
| Promptfoo | prompt/agent red-team and eval | governed agent registry | EVAL_CANDIDATE | P03 / P14 / P24 | cannot grant agent authority |
| Inspect AI | model/agent evaluation | governed agent registry | EVAL_CANDIDATE | P03 / P14 / P24 | evaluation framework only |

## 4. NEXUS-specific security rules

Semgrep/CodeQL/project-native rules should eventually detect or prevent patterns such as:

- agent code directly calling broker/exchange execution paths outside A6;
- A6 action without canonical A5 approval reference;
- attempted A5 or A8 veto bypass;
- credentials/API keys in source, tests, examples or logs;
- withdrawal-capable permission requests;
- unrestricted tool/plugin permissions;
- production endpoint hard-coding into test/dev code;
- dangerous subprocess/shell invocation;
- unsafe deserialization;
- unsanitized external content entering privileged prompts;
- missing idempotency on execution-side effects;
- missing authorization/freshness checks before sensitive action;
- security-sensitive config defaulting to permissive behavior.

Exact rules are implemented only after P02/P03/P04 define runtime languages, services and security architecture.

## 5. Phase ownership

### P03 — Security & Identity

Primary security-selection phase.

Evaluate/select:
- threat model;
- CodeQL baseline;
- Trivy baseline;
- Semgrep need;
- secrets/KMS solution;
- OPA policy model;
- SBOM model using Syft/CycloneDX;
- agent/LLM security using Promptfoo/Inspect AI;
- incident/emergency access controls.

Exit dependency: `G3_SECURITY_BASELINE`.

### P04 — Engineering Foundation

Convert selected controls into CI/build gates.

Expected controls:
- SAST in CI;
- dependency/CVE scan;
- secret scan;
- SBOM generation;
- license/dependency policy;
- signed release artifacts where adopted;
- provenance/attestations;
- deterministic policy gates;
- reproducible security evidence.

### P22 — Operations / Diagnostics / Recovery

Runtime/operations security:
- runtime observability;
- Falco evaluation if topology warrants;
- Trivy image/runtime artifact checks;
- credential compromise runbooks;
- alerting and incident evidence;
- backup/restore and recovery controls.

### P23 — UX / Team / Notifications

DAST and application attack-surface validation begins against authorized non-production environments:
- OWASP ZAP API/web scan;
- authentication/session flow checks;
- security headers/cookies/CSP once architecture exists.

### P24 — Controlled Production

Final security gate:
- CodeQL/SAST clean to policy threshold;
- dependency/CVE policy satisfied;
- SBOM complete;
- signed/provenance-verifiable artifacts if selected;
- DAST findings resolved to gate threshold;
- agent prompt/tool-abuse red-team passes;
- runtime/failure/recovery security tests pass;
- A8 independent verification;
- Human Gate remains mandatory for Live/Auto activation.

## 6. CI security pipeline direction

Target pattern, subject to P03/P04 selection:

```text
Source / PR
   |
Secret Protection
   |
SAST (CodeQL)
   |
Optional NEXUS custom rules (Semgrep)
   |
Trivy dependency/image/repo scan
   |
Syft -> CycloneDX SBOM
   |
Optional independent Grype SBOM verification
   |
Build
   |
Cosign / provenance
   |
Authorized test deployment
   |
OWASP ZAP
   |
Security evidence -> A8 / A10
```

## 7. Anti-overlap rules

- CodeQL is the preferred SAST baseline; Semgrep is for custom/project-specific coverage, not duplicate noise by default.
- Trivy is the preferred broad vulnerability/misconfiguration scanner candidate.
- Grype is an alternative or independent SBOM check, not mandatory parallel scanning.
- Syft is the preferred explicit SBOM generator candidate; CycloneDX is the canonical interchange family.
- Falco is not selected unless runtime architecture benefits from it.
- ZAP active scans are not run against third-party or production targets without explicit authorization.
- Do not adopt multiple secrets managers.
- Do not adopt multiple policy engines without measured justification.

## 8. Severity and fail-closed direction

Exact thresholds are set in P03/P04, but the baseline is:

- unresolved Critical vulnerability -> block sensitive release;
- unresolved secret exposure -> revoke/rotate and block;
- invalid/missing SBOM for governed release -> block;
- artifact signature/provenance mismatch -> block;
- A8 veto -> STOP;
- security state unknown for sensitive action -> fail closed;
- prompt/tool-injection indicator in privileged flow -> quarantine/escalate;
- unauthorized DAST target -> do not scan.

Exceptions require governed evidence and the required Human/Owner gate where policy specifies one.

## 9. Explicit non-decisions

This registry does not:
- install CodeQL, Trivy, Semgrep, ZAP, Falco or Grype;
- select a production secrets manager;
- create scanner credentials;
- expose repository secrets;
- modify production infrastructure;
- activate P03;
- change trading authority;
- enable Live Trading or Auto Trading.

Selection and installation occur in the owning roadmap phase under Task Contract and security/dependency gates.

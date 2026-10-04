# NEXUS QUANT — Supply Chain Security Baseline

STATE = P03-F IMPLEMENTATION
TASK = `FIN-P03-WF-001`
LINEAR = `HOS-168`
BASELINE = `FROZEN_G2`
DATE = 2026-10-04

## 1. Purpose

Define the security contract for source, dependencies, CI workflows, builders, SBOMs, provenance, signatures and promoted artifacts before P04 selects and activates concrete tools.

P03-F does not install scanners, modify runtime dependencies, sign production artifacts or provision signing infrastructure.

## 2. Protected supply-chain objects

- source revision and protected branch state;
- Task Contract / governance inputs;
- dependency manifests and lockfiles;
- third-party GitHub Actions and build tools;
- package registries / package archives;
- CI workflows and workflow identity;
- build environment and builder identity;
- generated artifact digest;
- SBOM;
- provenance / attestation;
- signature / certificate / transparency evidence;
- promotion/release decision;
- vulnerability/exception evidence.

## 3. Source and dependency policy

Dependencies MUST:
- come from an approved registry/source class;
- be resolved to an exact version/digest through the package manager lock mechanism;
- have attributable update history;
- be evaluated for known vulnerabilities, maintenance/health, licensing and security posture according to policy;
- avoid unreviewed install/postinstall execution where feasible;
- not be fetched from mutable or anonymous ad-hoc URLs for governed builds.

Rules:
- lockfile integrity is mandatory for reproducible governed dependency resolution;
- unexpected lockfile drift is a review signal;
- direct Git/archive dependencies require explicit immutable revision/digest;
- dependency replacement/source change is treated as a meaningful supply-chain change;
- transitive dependency risk is included, not ignored.

## 4. Third-party workflow/action policy

Third-party CI actions/tools:
- use reviewed publishers/sources;
- are pinned to immutable commit/digest where the platform allows;
- do not rely only on mutable tags for high-trust workflows;
- receive minimum token permissions;
- receive no secrets unless the exact job requires them;
- are reviewed before privilege expansion;
- are periodically re-evaluated for compromise/deprecation/security health.

Untrusted PR/fork code MUST NOT gain protected signing, deployment, broker, vault or production credentials.

## 5. CI identity and runner boundary

CI/build identity is separate from runtime identity.

Direction:
- short-lived/OIDC workload identity preferred over long-lived cloud secrets;
- workflow token permissions explicitly minimized;
- build/test verification and production promotion identities separated where practical;
- protected-environment approval can gate high-risk promotion later;
- untrusted code does not execute in a context holding protected production credentials;
- self-hosted runner use, if selected later, requires isolation/ephemeral cleanup policy;
- build environment provenance must identify builder/workflow/source inputs.

## 6. Secret protection in source/CI

Defense-in-depth direction:
- pre-commit/local detection may be used;
- repository secret scanning;
- push protection where supported;
- CI secret scanners;
- incident path for confirmed leak.

Secret scanning does not replace P03-C vaulting.

On secret exposure:
- revoke/rotate first;
- remove active plaintext references;
- preserve necessary forensic evidence;
- assess repository/history/cache/artifact/log exposure;
- do not assume deleting one commit invalidates a leaked credential.

## 7. Security analysis gate classes

P04 will select exact products/versions, but the required classes are:

### SAST
Source/code security findings.

Candidate baseline: CodeQL + Semgrep-class custom/policy rules.

### SCA / vulnerability
Dependencies, images/filesystems and known vulnerabilities.

Candidate baseline: Trivy; Grype may be secondary where useful.

### Misconfiguration / IaC
Configuration/container/IaC policy when those artifacts exist.

### Secret scanning
Repository/build artifact secret leakage.

### Custom policy
Project-specific invariants:
- no forbidden execution path;
- no raw secret exposure;
- required provenance/SBOM;
- dependency/action pinning;
- environment boundary constraints.

## 8. Severity and blocking direction

Default direction when controls activate:
- unresolved CRITICAL supply-chain security issue → BLOCK;
- HIGH issue → BLOCK unless explicit bounded exception policy permits;
- required SBOM missing/invalid → BLOCK governed promotion;
- required provenance missing/invalid → BLOCK;
- required signature/attestation mismatch → BLOCK;
- artifact digest differs from approved evidence → BLOCK;
- unknown/untrusted builder identity for production-capable artifact → BLOCK.

Exact thresholds and scanners become P04 contracts.

## 9. SBOM

Canonical direction:
- generate SBOM from the actual resolved/build context;
- bind SBOM to artifact/source/build evidence;
- store SBOM as immutable release evidence;
- include first-party and third-party components/dependency relationships;
- preserve generator/version/spec metadata;
- retain according to artifact/evidence lifecycle.

Preferred interoperable representation:
- CycloneDX 1.7 as primary machine-readable candidate;
- SPDX interoperability remains supported/acceptable where downstream tooling requires it.

P04 makes the concrete format/tool decision and validates schema/toolchain compatibility.

## 10. Provenance / SLSA direction

Use SLSA v1.2 concepts for provenance and build hardening.

Every governed release artifact should eventually be verifiable against:
- artifact digest;
- source repository/revision;
- builder/workflow identity;
- build invocation/configuration;
- relevant materials/inputs;
- build timestamps/metadata;
- provenance predicate/attestation.

Initial target direction:
- provenance MUST exist for governed artifacts;
- provenance generated by the build process, not handwritten post hoc;
- promotion verifies provenance subject digest against artifact;
- higher environments require stronger builder/provenance trust.

P04 determines achievable SLSA Build level and implementation.

## 11. Artifact signing / verification

Direction:
- artifact identity is digest-first;
- signing/attestation binds approved identity and provenance to that digest;
- verify before promotion/deployment;
- verification policy checks expected signer/workflow identity and issuer/trust root;
- signature success alone does not override vulnerability, policy, Risk or Security gates.

Preferred candidate:
- Sigstore/Cosign class signing and verification;
- identity-based/keyless CI signing is preferred where governance/trust requirements are met;
- KMS-managed signing key remains a permitted alternative where required.

No signing root/key is provisioned by P03-F.

## 12. Build reproducibility / hermeticity direction

Governed build should minimize uncontrolled inputs.

Requirements direction:
- pinned toolchain/dependencies;
- declared inputs;
- clean build context;
- avoid network fetches outside declared dependency/material resolution where feasible;
- deterministic artifact digest where technically achievable;
- record non-deterministic inputs when unavoidable.

Reproducibility is evidence, not a substitute for provenance.

## 13. Promotion contract

Promote an immutable artifact, never “whatever is currently on the branch.”

Promotion input:
- artifact digest;
- source revision;
- CI/run identity;
- SBOM;
- provenance;
- signature/attestation;
- scanner/policy results;
- environment target;
- rollback artifact;
- approval/gate evidence where required.

A promotion must fail closed on required evidence mismatch.

## 14. Dependency update policy

Updates are governed changes.

For security-critical dependencies:
- urgent security update path exists;
- evidence identifies prior/new version and vulnerability rationale;
- tests/regression evidence still required;
- emergency does not mean bypassing provenance.

Routine updates:
- automated proposals are allowed;
- merge remains governed by tests/policy;
- auto-merge, if later enabled, is restricted to explicitly defined low-risk classes.

## 15. Exception / waiver policy

A waiver is not “ignore forever.”

Every exception has:
- exception ID;
- exact finding/package/control;
- severity;
- rationale;
- compensating control;
- owner;
- affected environment/artifact;
- created/approved times;
- expiry/review date;
- evidence;
- remediation plan.

Rules:
- CRITICAL exception requires highest governed approval and normally blocks production;
- expired exception fails closed;
- an exception cannot waive signature/provenance identity mismatch for production-capable release without explicit later G4/P24 policy;
- no blanket repository-wide permanent waiver.

## 16. Compromise response

Suspected dependency/action/package/build compromise:
1. halt affected promotion/release path;
2. identify impacted source/build/artifact digests;
3. revoke compromised signing/workflow credentials if applicable;
4. invalidate affected artifact eligibility;
5. rebuild from trusted source/builder after remediation;
6. regenerate SBOM/provenance/signature;
7. investigate downstream deployed/use scope;
8. record incident/evidence;
9. verify repaired artifact independently before resume.

## 17. Open-source dependency evaluation

Evaluation signals may include:
- vulnerability history and response;
- maintenance activity;
- release provenance;
- maintainer/project security process;
- dependency footprint;
- license compatibility;
- known compromise history;
- package-name confusion/typosquatting risk;
- OpenSSF Scorecard-class evidence where useful.

Popularity alone is not trust.

## 18. Tool candidate handoff to P04

The existing Security Tooling Baseline remains authoritative candidate guidance.

P04 should evaluate/activate:
- CodeQL;
- Semgrep;
- Trivy;
- optional Grype;
- Syft/CycloneDX or equivalent SBOM generator;
- Cosign/Sigstore;
- SLSA-compatible provenance/attestation;
- OpenSSF Scorecard as supporting evidence where useful.

P03-F defines required outcomes, not vendor/tool lock-in.

## 19. Required downstream tests

- mutable third-party action tag in protected workflow → policy failure;
- untrusted PR attempts protected secret access → denied;
- lockfile drift without manifest intent → detected;
- known blocked vulnerability → promotion denied;
- missing required SBOM → denied;
- artifact digest != SBOM/provenance subject → denied;
- missing/invalid provenance → denied;
- unexpected signer/workflow identity → denied;
- modified artifact after signing → verification fails;
- expired waiver → denied;
- compromised dependency response drill;
- rebuild emits fresh evidence tied to repaired source revision.

## 20. Current implementation state

Concrete SAST/SCA scanners: NOT_ACTIVATED_BY_P03-F  
SBOM generator: NOT_SELECTED_FOR_RUNTIME_GATE  
Signing infrastructure: NOT_PROVISIONED  
Provenance generator: NOT_ACTIVATED  
SLSA level: NOT_CLAIMED  
Production release: DISABLED  
CANARY: DISABLED  
LIVE: DISABLED  
AUTO_TRADING: DISABLED

This is a canonical security baseline only.

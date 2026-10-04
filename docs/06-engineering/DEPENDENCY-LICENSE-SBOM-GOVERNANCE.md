# NEXUS QUANT — Dependency / License / SBOM Governance

STATE = P04-F IMPLEMENTATION
TASK = `FIN-P04-WF-001`
LINEAR = `HOS-177`
DATE = 2026-10-04

## 1. Purpose

P04-F activates the concrete supply-chain controls required by P03-F for dependencies, licenses, vulnerabilities and SBOM evidence.

This workstream is intentionally narrow:
- dependency/source policy;
- license policy;
- vulnerability/misconfiguration/secret scan;
- CycloneDX SBOM;
- waiver governance.

It does not provision signing keys, production deployment identity or Live trading.

## 2. Selected tools

### SBOM

- generator: Syft
- version: `1.54.0`
- action: `anchore/sbom-action` release `v0.24.3`
- immutable action commit: `66cbf4bc1f1c0d2edc94016e65bc221b6bb0ad6c`
- output: CycloneDX JSON
- CycloneDX spec: `1.7`

Syft 1.54.0 exposes CycloneDX 1.7 as its default/current JSON schema version.

### Vulnerability / misconfiguration / secret scan

- scanner: Trivy
- version: `0.75.0`
- action: `aquasecurity/trivy-action` release `v0.36.0`
- immutable action commit: `ed142fd0673e97e23eac54620cfb913e5ce36c25`

P04-F runs filesystem scanning for:
- vulnerabilities;
- misconfiguration;
- secret findings.

Blocking severities:
- CRITICAL = BLOCK
- HIGH = BLOCK

MEDIUM/LOW remain report-only at this baseline.

## 3. Dependency policy

Canonical registries:
- npm: `https://registry.npmjs.org/`
- Python: `https://pypi.org/simple`

Direct production/dev dependency declarations must be:
- exact SemVer for npm/pnpm; or
- explicit `workspace:` protocol for repository-internal packages;
- exact `==` PEP 440 pins for Python.

Forbidden:
- `latest`;
- `*`;
- caret/tilde floating ranges;
- mutable Git branch/tag dependency;
- unpinned URL/archive dependency.

Transitive exactness is carried by committed lockfiles.

## 4. License policy

P04-F uses three states.

### ALLOW

Permissive/common licenses approved by engineering policy may pass automatically.

### REVIEW

Copyleft/reciprocal licenses that may be usable only in a specific linking/distribution context do not pass automatically. They require an exact, active `LICENSE_REVIEW` waiver with scope, rationale and expiry.

### BLOCK

Licenses intentionally incompatible with the default distribution/service posture are blocked by baseline policy.

Unknown, missing or `NOASSERTION` third-party license also fails closed pending review.

This engineering policy is not legal advice.

### Curated version-bound assertions

When an SBOM generator omits license metadata for a **known toolchain component**, P04-F may use a narrowly-scoped assertion only when all of the following are true:
- the component identity includes an exact package/version identity;
- the license is verified from the component's official tagged source;
- evidence and scope are recorded in `config/supply-chain/license-policy.json`;
- a version change does not inherit the assertion automatically.

Baseline assertion:
- identity prefix: `pkg:npm/%40pnpm/`
- exact version: `11.28.4`
- license: `MIT`
- evidence: official `pnpm/pnpm` tag `v11.28.4` LICENSE.

The assertion is constrained by both namespace and exact version. A pnpm version change requires a new review/assertion; components outside the `@pnpm` namespace are unaffected. Unknown-license fail-closed behavior remains unchanged.

## 5. Waivers

A waiver is explicit and temporary.

Required:
- unique ID;
- kind;
- exact subject;
- severity/class;
- rationale;
- compensating control;
- owner;
- environments;
- approved time;
- expiry;
- evidence;
- remediation plan.

Expired or incomplete waiver fails closed.

There are no active P04-F waivers at baseline.

## 6. Trivy ignore parity

`.trivyignore` is not an independent escape hatch.

Every non-comment entry must correspond exactly to an active, unexpired `VULNERABILITY` waiver in:

`config/supply-chain/waivers.json`

An ignore without governed waiver fails CI.

## 7. SBOM validation

Required:
- `bomFormat = CycloneDX`;
- `specVersion = 1.7`;
- component inventory present;
- third-party components have license evidence;
- license decision is ALLOW or covered by an active exact REVIEW waiver;
- blocked licenses never pass automatically.

First-party package `nexus-quant` is exempt from third-party license declaration enforcement.

## 8. CI gate

Required `governance` context performs:

1. dependency/waiver policy validation;
2. Syft CycloneDX 1.7 generation;
3. SBOM/license validation;
4. Trivy HIGH/CRITICAL vulnerability/misconfiguration/secret scan;
5. deterministic supply-chain evidence summary;
6. artifact upload.

Any blocker causes the required status context to fail.

## 9. Dependency automation

Automated dependency proposal tooling is intentionally not activated before the first real runtime dependency exists.

Policy:
- automated proposals may be activated later;
- auto-merge remains disabled;
- security updates receive urgent governed review;
- routine updates remain governed batches.

## 10. Deferred controls

Not falsely claimed by P04-F:
- CodeQL/Semgrep SAST activation;
- production artifact signing;
- KMS/keyless signing identity;
- production SLSA provenance gate;
- deployment/promotion verification.

These remain downstream controlled work.

## 11. Safety

Production dependency auto-merge: DISABLED  
Signing identity/key: NONE  
Production deployment: NONE  
Production account/credential: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Next

After canonical closure:

`P04-G — Developer Bootstrap & Tooling`

P04-G is not started by P04-F.

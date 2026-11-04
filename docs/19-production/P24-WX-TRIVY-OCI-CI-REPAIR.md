# P24-WX-001 — Required Trivy Security CI Repair / OCI Scan With Pinned Digest

**Tracking:** [Issue #518](https://github.com/rahemih/Finance/issues/518). **Task:** `FIN-P24-WX-001`. **Prepared:** 2026-11-04. **Owner gate:** new independent PR-specific exact HEAD + Governance Artifact SHA256 required; this change is not authorized by PR #517's earlier merge consent.

## 1. Incident and exact failure

PR #517 was lawfully Squash-MERGED into protected main `bb33ffd8d25c941cd299878a5697a460d1b8df07`. Premerge required Governance #41446490461 passed 239 checks (319 P24 tests); postmerge [Governance #41779026384](https://github.com/rahemih/Finance/actions/runs/41779026384) failed in **three attempts** because upstream `aquasecurity/trivy-action` could not download/install its pinned Trivy v0.75.0 Linux binary from GitHub release assets. The installer located the release then returned `exit code 6`. Trivy security scanning never actually started, no `build/trivy.json` or final `foundation-ci-manifest` existed. [Branch Hygiene #41779026385](https://github.com/rahemih/Finance/actions/runs/41779026385) passed.

**No vulnerability scan result was obtained**. This is neither a clean security report nor evidence of a product vulnerability; the exact runner DNS/egress cause of curl exit 6 has not been independently diagnosed. All three attempts generated valid 319 P24 unit-test and strict typecheck results, which do **not** substitute for this mandatory scanner.

## 2. Official immutable scanner distribution

To remove *only the failing GitHub Releases installer dependency*, switch to the official Trivy container image published by Aqua Security:

- [Trivy official installation guide](https://www.trivy.dev/docs/latest/getting-started/installation/) identifies `docker.io/aquasec/trivy` as an official scanner distribution.
- [Official Docker Hub v0.75.0 linux/amd64 image](https://hub.docker.com/layers/aquasec/trivy/0.75.0/images/sha256-9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283) reports the immutable architecture-specific manifest SHA256 `9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283`, and multi-platform index SHA256 `af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa`.
- CI invokes `docker.io/aquasec/trivy@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283`, explicitly `linux/amd64`. No floating tag, unverified image, installer `curl | sh` or new GitHub Action version.
- CI checks actual container output `Version: 0.75.0` **before scanning**. The project dependency policy `scanner_version=0.75.0` is unchanged.

**Important:** The Digest guarantees the identity of the image pulled from Docker Hub; the GitHub-hosted runner must actually be able to pull the image *and* Trivy's vulnerability/misconfiguration databases. Neither availability nor scanner success is assumed before actual CI execution.

## 3. Security controls preserved and strengthened

The scanner continues to perform a filesystem scan of the same repository directory with all original options: `--scanners vuln,misconfig,secret`, `--severity HIGH,CRITICAL`, `--exit-code 1`, `--ignore-unfixed=false`, `--ignorefile .trivyignore`, `--format json`.

The container has an **immutable pinned manifest**, read-only source checkout and container root filesystem, no Docker socket, no-new-privileges, no capabilities, runs under the GitHub runner's unprivileged UID/GID, mounts only `build` writable at `/scan-output`, and uses temporary cache. Network is available solely because vulnerability DB updates are a required scanner dependency. Any failed image pull, DB fetch, scan command, empty report, invalid JSON, HIGH/CRITICAL vulnerability or required downstream evidence step must fail the job.

Existing Syft CycloneDX 1.7 SBOM generation, source-waiver matching, dependency and license policies, `supply_chain_evidence.py`, `foundation_ci.py` and mandatory artifact upload remain unchanged. A scanner run generating a JSON file with high-severity findings must fail the gate, not be accepted as a clean report.

The new `tests/p24/test_trivy_oci_runner.py` contains static negative-policy assertions that refuse mutable tags, scanner narrowing, missing JSON gates and weakened isolation. Unit test success proves only a good workflow **specification**, not that the Trivy scanner actually ran.

## 4. Acceptance matrix and non-waivable Human Gate

| Objective evidence | Before merge | After merge |
| --- | --- | --- |
| Exactly five allowlisted paths (task contract, workflow, tests, this doc, Task Catalog) | Required | Recheck |
| Full GitHub Governance on exact PR HEAD | Must be SUCCESS including **real OCI Trivy invocation** | Must be SUCCESS on resulting protected main |
| Trivy v0.75.0 architecture manifest + version check | Must prove pinned image ran | Must prove pinned image ran |
| `build/trivy.json` complete, valid and no HIGH/CRITICAL blocking finding | Mandatory | Mandatory |
| Syft SBOM, license/waiver, evidence summary + foundation manifest | Mandatory | Mandatory |
| No loss of CI, A5 risk veto, A8 security and A10 evidence hard gates | Required | Required |
| PR-specific exact-HEAD + unexpired Artifact SHA256 Owner Human Gate | Required before merge | Preserve evidence |
| Branch Hygiene required checks | Enforced by policy | Must pass |
| GitHub #518 and Linear reconciled | Keep OPEN until verified | Close #518 **only** after accepted postmerge evidence |

**Do not** allow `continue-on-error`, `exit-code 0`, ignored HIGH/CRITICAL vulnerabilities, source exclusions, `ignore-unfixed=true`, disabled scanner engines, or non-immutable image tags to make CI green. Even if the new OCI image cannot be pulled in CI, the correct decision is `BLOCKED / NO SCAN`, not `PASS`.

## 5. Trading and production readiness boundary

No Demo/Live orders, credentials, MT5 terminal access, broker-selection, data-source approval or readiness policy changes occur in this workstream. NEXUS QUANT P24-A remains assessment-only, P24-B BLOCKED, P24-C..I NOT_STARTED, all 9 PRE_FIRST_LIVE false, first Live Owner gate not granted, G13 NOT_STARTED and Live/Auto DISABLED. PR #517 remains merged but postmerge security verification pending until this governed repair obtains full, independently attested postmerge evidence.

**Current deliverable:** proposed critical CI repair PR; don't claim issue #518 resolved without complete required test and approval sequence.

# P24-CI — Recovery plan for mandatory Trivy install failure (#518)

**Task:** `FIN-P24-WU-001-R01` — **CRITICAL / separate A5-A8-A10 and Owner exact-head Human Gate**.  
**Prepared:** 2026-11-04.  
**Source incident:** [GitHub issue #518](https://github.com/rahemih/Finance/issues/518); [PR #517](https://github.com/rahemih/Finance/pull/517) is already merged at `bb33ffd8d25c941cd299878a5697a460d1b8df07`.

## 1. Reproducible incident facts, not an invented clean scan

[Required postmerge Governance run #41779026384](https://github.com/rahemih/Finance/actions/runs/41779026384) failed on all three attempts at **Trivy supply-chain scan**. Log shows Aqua Security install helper correctly resolves v0.75.0/Linux/64bit then exits 6 during install, **before any Trivy binary or vulnerability scan executes**. Exact network error is not printed by the installer, so it remains unverified whether the cause is DNS, asset-host egress, a proxy or another transport issue. The other required pre-scan checks passed, including 319 P24 unit tests and strict Pyright. [Branch Hygiene #41779026385](https://github.com/rahemih/Finance/actions/runs/41779026385) succeeded. **No postmerge foundation manifest exists** for #517; it cannot be declared POSTMERGE_PASS.

This is a required security control outage, not evidence that the scanned repository has no HIGH/CRITICAL findings. Do not mark Issue #518 resolved until actual scanner execution is evidenced.

## 2. Replacement stays the *same exact scanner and same blocking policy*

[Official Aqua Security installation guide](https://www.trivy.dev/docs/latest/getting-started/installation/) lists both official OCI distributions and GitHub Release assets. The official [GHCR Trivy v0.75.0 package](https://github.com/aquasecurity/trivy/pkgs/container/trivy/1321934415?tag=0.75.0) and the official [Docker Hub linux/amd64 image](https://hub.docker.com/layers/aquasec/trivy/0.75.0/images/sha256-9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283) identify the same immutable **linux/amd64 OCI manifest**:

`sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283`

Use *only* `ghcr.io/aquasecurity/trivy@sha256:9db...` or, if pull fails, the official `docker.io/aquasec/trivy@sha256:9db...` at the **same full digest**. The Docker engine verifies the image against its content digest. No floating tags, latest, unverified mirror or arbitrary binary downloads. Require the container to report `Version: 0.75.0` before scanning.

The replacement runner `scripts/ci/run_trivy_oci.sh` launches a non-root container with read-only root filesystem and code mount, no Docker socket, no elevated capabilities, no-new-privileges, and only the necessary writable vulnerability-DB cache and Trivy JSON output mount. Network is **enabled** for the current Trivy vulnerability database. A network/image/cache/DB failure is a **hard failure**.

**Full scan gate unchanged:** `fs` against the full repository; scanners `vuln,misconfig,secret`; severities `HIGH,CRITICAL`; `--exit-code 1`; no `ignore-unfixed` suppression; governed `.trivyignore` unchanged. No `continue-on-error`, `--skip-db-update`, `--offline-scan`, skipping JSON, or lowering a severity threshold.

The runner requires valid fresh `build/trivy.json` and invokes `scripts/ci/verify_trivy_scan.py` which independently validates filesystem report schema and denies any HIGH/CRITICAL vulnerability, misconfiguration or exposed secret. Existing mandatory Syft SBOM/license check and `supply_chain_evidence.py` run afterwards, unchanged. Full Governance workflow and release gates remain mandatory.

## 3. Evidence matrix — no false positives

| Input or real environment | Expected behavior / authority |
| --- | --- |
| Exact official digest reachable, correct v0.75.0 binary, current DB and clean full scan JSON | *May pass only after actual Trivy runs*, JSON verifier passes, and unchanged SBOM/license/evidence steps pass |
| GHCR pull error, official Docker Hub *same immutable digest* reachable | Allowed bounded official fallback, still executes full scan; no scanner bypass |
| Both registries unavailable, wrong image version, DB download unavailable | **FAIL_CLOSED**; do not generate or accept a fake report |
| Nonzero scanner exit on HIGH/CRITICAL vuln/misconfig/secret | **FAIL_CLOSED**; no `|| true` or warning-only behavior |
| Stale, missing, truncated, malformed, invalid-schema JSON | **FAIL_CLOSED**, even if some preceding step returned zero |
| Synthetic fake-Docker test is green | Proves only script error-handling; **not** an actual CVE scan, A8/A10 signoff or production readiness |
| New PR has green unit tests but real scan fails to download DB/image | Required Governance **FAILURE**; remain open and diagnose next dependency without replacing security controls |

**CI acceptance must verify:** full strict Typecheck, existing P24 unit tests, *real* Trivy v0.75.0 invocation with complete JSON produced under `build/trivy.json`, independent JSON validation, unchanged supply-chain summary, reproducible clean-source build and unexpired exact HEAD `foundation-ci-manifest`. PR-specific A5/A8/A10 and **separate Owner HEAD + Artifact SHA256 Human Gate** are required before protected merge. Exact-main postmerge Governance and Branch Hygiene success required afterwards, and only then close #518 with a traceable evidence link.

## 4. Work boundaries and rollback

Exactly **seven files** may change: this document, HIGH/CRITICAL task contract, `docs/13-tasks/TASK-CATALOG.md`, `.github/workflows/governance.yml` **Trivy step only**, `scripts/ci/run_trivy_oci.sh`, `scripts/ci/verify_trivy_scan.py`, `tests/foundation/test_trivy_oci_contract.py`. No frozen roadmap or production configuration changes; no CVE waivers, no scanner reductions and no live/auto permissions.

This repairs the **security-tool installation path** only; it does not remedy the original absence of user-local MT5 compile/probe data, broker clock attestation, sanctioned broker order tests or actual operational Kill Switch certification. All nine `PRE_FIRST_LIVE` remain false; P24-B BLOCKED, G13 NOT_STARTED, Live/Auto DISABLED. [Demo #508](https://github.com/rahemih/Finance/issues/508) and [Live #491](https://github.com/rahemih/Finance/issues/491) stay OPEN.

If this candidate fails, do not merge on a bypass. Revert only the changed seven files via governed review, preserve the security failure and investigate exact missing dependency. No fix attempt may claim postmerge PASS on PR #517 unless that exact SHA actually passed its original full scanner, or cite the independently verified *new remediation main SHA* with proper provenance as the updated baseline.

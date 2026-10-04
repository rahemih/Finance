# NEXUS QUANT — Reproducible Build / Artifact Verification

STATE = P04-H IMPLEMENTATION
TASK = `FIN-P04-WH-001`
LINEAR = `HOS-179`
DATE = 2026-10-04

## 1. Purpose

P04-H closes the Engineering Foundation by proving that the same governed source revision can be exported into independent clean trees, bootstrapped with locked dependencies and converted into byte-identical rollback-ready artifacts.

P04 currently contains engineering foundation code/contracts/tests, not an application or market runtime. Therefore this task does **not** claim a production binary/container exists.

The canonical P04 artifact is a reproducible source/config foundation bundle. Later executable/container artifacts extend the same verification contract.

## 2. Clean-source model

The required CI runner is already ephemeral.

P04-H adds two independent source trees created from:

`git archive HEAD`

Each tree therefore contains tracked source only.

Before artifact build, each clean tree must pass:
- `pnpm install --frozen-lockfile --ignore-scripts`;
- `uv sync --locked --no-install-project`;
- `python scripts/dev/doctor.py --ci`.

Corepack owns pnpm version selection in CI. The clean-build step sets `PNPM_CONFIG_MANAGE_PACKAGE_MANAGER_VERSIONS=false` so pnpm does not attempt to maintain a separate package-manager environment lock inside an exported source tree. This does not relax application dependency locking: `--frozen-lockfile` remains mandatory.

This proves that declared toolchains and lockfiles are sufficient on a clean source export.

## 3. Canonical artifact

Output:

`foundation-source.tar`

The artifact contains the governed source/config tree with normalized tar metadata:
- lexical path ordering;
- mtime = 0;
- uid/gid = 0;
- empty owner/group names;
- regular file mode normalized to 0644 or 0755 according to executable bit;
- symlink target preserved deterministically.

Generated paths are excluded:
- `.git`;
- `node_modules`;
- `.venv`;
- `build`;
- `dist`;
- cache/test/tool temporary directories.

Because the source tree originates from `git archive`, untracked local files and local secret files cannot enter the artifact.

## 4. Rollback manifest

Output:

`rollback-manifest.json`

It records:
- exact source commit SHA;
- canonical artifact name;
- artifact SHA-256;
- artifact byte size;
- deterministic full file inventory;
- each file path, type, normalized mode, size and SHA-256;
- file-inventory digest;
- exact Node / pnpm / Python / uv baseline;
- safety markers.

No timestamp is included, so repeated builds are byte-comparable.

## 5. Reproducibility requirement

CI builds artifact A and artifact B from two independent clean exports.

Required:
- artifact A bytes == artifact B bytes;
- manifest A bytes == manifest B bytes;
- both verifier runs PASS;
- source SHA in manifest == CI commit SHA.

Any mismatch blocks the required `governance` status.

## 6. Tamper verification

The verifier fails closed when:
- artifact SHA differs from manifest;
- source SHA differs from expected source;
- archive contains absolute or traversal paths;
- archive member set differs from manifest;
- file/symlink content digest differs;
- normalized mode/type/size differs;
- excluded generated path is present.

## 7. Rollback readiness

At P04, rollback means restoring the exact governed engineering foundation revision represented by:
- source SHA;
- verified source/config artifact;
- rollback manifest;
- accompanying SBOM, Trivy and CI evidence.

Promotion/deployment rollback remains downstream because production deployment is not active.

## 8. CI artifact set

The required Foundation CI evidence upload includes:
- deterministic foundation manifest;
- deterministic test-harness evidence;
- CycloneDX 1.7 SBOM;
- Trivy JSON report;
- supply-chain summary;
- `foundation-source.tar`;
- `rollback-manifest.json`.

## 9. P04 exit criteria

P04 can close only when:
- P04-A through P04-G are already CANONICAL_COMPLETE;
- P04-H reproducibility gate passes on PR and post-merge main;
- rollback artifact/manifest are present;
- required `governance` remains protected;
- P04-H closure is merged and lock released.

No named roadmap gate is invented for P04; the roadmap defines P04 completion as Engineering Foundation readiness before P05.

## 10. Safety

Application/market runtime artifact: NOT_YET_EXISTS  
Production deployment: NONE  
Production infrastructure/accounts/credentials: NONE  
Signing/KMS identity: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 11. Next phase

After P04 canonical closure:

`P05 — Real-Time Data`

P05 remains `NOT_STARTED` until explicit Owner authorization to enter the next phase.

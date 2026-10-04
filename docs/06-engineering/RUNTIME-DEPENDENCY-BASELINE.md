# NEXUS QUANT — Language / Runtime / Dependency Baseline

STATE = P04-B IMPLEMENTATION
TASK = `FIN-P04-WB-001`
LINEAR = `HOS-173`
DATE = 2026-10-04

## 1. Objective

Create a reproducible language/runtime/package-management baseline before CI/CD and market-system implementation.

P04-B establishes exact tool versions and lockfile rules. It does **not** implement the CI/CD pipeline, market logic, infrastructure, or production credentials.

## 2. Canonical runtime baseline

| Capability | Canonical version | Decision |
|---|---:|---|
| Node.js | `24.21.0` | LTS baseline |
| TypeScript | `7.0.2` | stable language/compiler baseline |
| pnpm | `11.28.4` | canonical JS/TS package manager |
| Python | `3.14.8` | stable Python baseline |
| uv | `0.12.23` | canonical Python project/dependency manager |
| PydanticAI | `2.54.0` | architecture-selected agent runtime pin; installation deferred until runtime package exists |

## 3. Version-selection rationale

### Node.js

Node 24.21.0 is selected because it is an LTS line on the task date.

Node 26.10.0 is newer but remains Current on 2026-10-04. NEXUS QUANT prefers the LTS line for the engineering foundation rather than adopting a Current release immediately before its LTS transition.

### Python

Python 3.14.8 is selected as the current stable feature-series maintenance release.

Python 3.15.0 is not selected because, on 2026-10-04, 3.15.0rc3 is still a release candidate and the final release is scheduled after the task date.

### TypeScript

TypeScript 7.0.2 is the stable baseline. Exact compiler installation occurs only in a package that needs TypeScript; the root repository records the language version but avoids adding a dependency merely to populate the root.

### pnpm

pnpm 11.28.4 is selected even though pnpm 12.9.1 is newer.

Reason: pnpm 12 commonly emits a multi-document `pnpm-lock.yaml` when package-manager pinning is active. Current ecosystem reports show dependency graph/SBOM consumers can read only the first document and miss the project dependency graph. Since P04-F requires trustworthy SBOM/dependency evidence, pnpm 12 is deferred until those consumers are verified compatible.

State:

`PNPM_12_UPGRADE = DEFERRED_REVALIDATION`

### uv

uv 0.12.23 is selected as the Python package/project manager. Its locked/frozen workflows align with reproducible environments and its workspace model supports a shared lockfile.

### PydanticAI

FROZEN_G2 selected PydanticAI as the primary agent runtime adapter behind the project-owned Governance Kernel.

P04-B records `pydantic-ai==2.54.0` as the approved initial version pin. It is **not installed at repository root** because the Agent Control Plane package has not yet been materialized. Adding it before an owning package exists would create an artificial root production dependency.

## 4. Repository runtime markers

Node:
- `.node-version` = `24.21.0`
- `package.json.engines.node` = exact `24.21.0`
- `package.json.devEngines.runtime` = exact Node runtime
- `package.json.packageManager` = `pnpm@11.28.4`

Python:
- `.python-version` = `3.14.8`
- `pyproject.toml.requires-python` = `==3.14.*`
- `uv.lock` carries the Python 3.14 compatibility baseline.

## 5. Workspace/package-manager policy

JavaScript/TypeScript:
- pnpm is the only canonical JS/TS package manager.
- one shared workspace lockfile: `pnpm-lock.yaml`.
- workspace package linkage must use explicit `workspace:` protocol when package dependencies are introduced.
- direct dependencies are saved exactly by default.
- dependency declarations without committed lockfile reconciliation are invalid.

Python:
- uv is the canonical Python project/dependency manager.
- `pyproject.toml` is the declaration source.
- `uv.lock` is committed.
- clean/reproducible sync consumes the lockfile without silently upgrading it.
- future Python workspace members are added only when real packages exist.

## 6. Lockfile policy

Lockfiles are canonical source-controlled evidence.

Rules:
1. dependency declaration and corresponding lockfile change are reviewed together;
2. ordinary build/test commands may not silently upgrade lockfiles;
3. dependency upgrade tasks must be explicit and attributable;
4. lockfiles are regenerated only with the canonical package-manager major/version;
5. a tool-version change requires its own governed task or an explicitly scoped P04/P22 maintenance task;
6. CI in P04-C must use immutable/locked installation mode.

Initial root lockfiles intentionally contain **no production application dependencies**. They establish deterministic manager/format baselines before domain packages exist.

## 7. Dependency pinning policy

Default:
- package-manager/runtime versions: exact;
- direct production dependencies: exact on introduction;
- transitive resolution: lockfile exact;
- Git dependencies: immutable commit SHA only when unavoidable;
- branch/tag Git dependencies are forbidden for production;
- pre-release dependencies require an explicit exception;
- unbounded `latest`, `*`, floating URL or mutable branch references are forbidden in production manifests.

Exceptions require:
- owning task;
- reason;
- Security review where supply-chain relevant;
- rollback plan;
- expiry/review condition.

## 8. Upgrade policy

Runtime/toolchain review:
- security release: evaluate immediately;
- patch release: batch through governed maintenance;
- minor release: compatibility review;
- major release: explicit migration task with reproducibility/security evidence.

A newer version is not sufficient reason to upgrade.

For pnpm 12 specifically, upgrade requires evidence that:
- GitHub dependency graph correctly reads the project graph;
- Syft/CycloneDX generation reads all lockfile documents;
- selected vulnerability scanners do not omit project dependencies;
- clean install/lock verification remains deterministic.

## 9. Reproducible local contract

Canonical expectations:

JS/TS:
```text
Node 24.21.0
pnpm 11.28.4
pnpm install --frozen-lockfile
```

Python:
```text
Python 3.14.8
uv 0.12.23
uv sync --locked
```

Exact bootstrap UX and cross-platform setup automation belong to P04-G. CI enforcement belongs to P04-C.

## 10. Security constraints

- no package lifecycle script is implicitly trusted merely because a package was resolved;
- registry/source trust remains governed by P03-F and P04-F;
- no raw secrets in package-manager config;
- lockfile review does not replace SCA/SBOM/signature/provenance controls;
- known package-manager/scanner incompatibility fails closed for promotion.

## 11. Safety

Production application dependencies installed by P04-B: NONE  
Broker/exchange/provider connections: NONE  
Production infrastructure: NONE  
Credentials/accounts/funding/orders: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 12. Next workstream

After canonical closure only:

`P04-C — CI/CD Foundation`

P04-C is not started by this task.

# NEXUS QUANT — Developer Bootstrap & Tooling

STATE = P04-G IMPLEMENTATION
TASK = `FIN-P04-WG-001`
LINEAR = `HOS-178`
DATE = 2026-10-04

## 1. Purpose

P04-G gives developers one repository-native way to prepare, diagnose and validate the engineering environment without adding another framework or IDE dependency.

CI remains authoritative. Local tools accelerate feedback; they never waive repository Governance, Security or Supply-Chain gates.

## 2. Canonical commands

Direct Python commands:

```text
python scripts/dev/doctor.py
python scripts/dev/bootstrap.py
python scripts/dev/local_gate.py fast
python scripts/dev/local_gate.py full
python scripts/dev/install_hooks.py
```

Equivalent pnpm aliases:

```text
pnpm doctor
pnpm bootstrap
pnpm check:fast
pnpm check:full
pnpm test:foundation
pnpm hooks:install
```

## 3. Doctor

`doctor.py` validates:
- repository root;
- Git availability;
- Python = `3.14.8`;
- Node.js = `24.21.0`;
- pnpm = `11.28.4`;
- uv = `0.12.23`;
- canonical marker/manifests exist and agree.

Modes:
- normal text;
- `--json` for machine-readable diagnostics;
- `--ci` for strict CI use.

The doctor does not enumerate environment variables and does not inspect or print secret values.

## 4. Bootstrap

`bootstrap.py`:
1. validates canonical Python/Node/Git availability;
2. enables Corepack;
3. activates exact pnpm `11.28.4`;
4. runs `pnpm install --frozen-lockfile --ignore-scripts`;
5. requires exact uv `0.12.23`;
6. runs `uv sync --locked --no-install-project`;
7. runs strict doctor;
8. runs the fast local gate;
9. optionally installs Git hooks with `--hooks`.

Bootstrap deliberately does **not** download uv through a remote shell script or modify production credentials.

If uv is absent/wrong, bootstrap fails with the expected version; installation remains an explicit developer/machine-management action.

## 5. Local gates

### fast

Runs low-cost repository checks:
- governance baseline;
- branch-name policy where applicable;
- foundation lint;
- typecheck readiness;
- CI foundation self-tests;
- forward task-contract validation;
- config contract;
- foundation unittest suite;
- dependency/waiver manifest policy;
- workflow security;
- promotion fail-closed check.

### full

Runs:
- strict doctor;
- pnpm frozen lock sync with lifecycle scripts disabled;
- uv locked sync;
- the full fast gate.

Syft and Trivy remain authoritative CI gates; local full checks do not pretend to replace the pinned CI scanner environment.

## 6. Git hooks

Hooks are **opt-in convenience**, not authority.

Installer:
- targets `.git/hooks/pre-commit` and `.git/hooks/pre-push`;
- refuses to overwrite an existing hook by default;
- `--force` is required to replace;
- forced replacement first creates a deterministic `.nexus-quant.bak` backup;
- pre-commit runs fast gate;
- pre-push runs full gate.

CI remains required even if hooks are disabled or bypassed locally.

## 7. Cross-platform policy

Orchestration is Python standard library and avoids shell-specific bootstrap logic.

Supported developer OS families:
- Windows;
- macOS;
- Linux.

The Git hook templates are POSIX shell wrappers because Git for Windows executes hooks through its shell compatibility layer.

## 8. Debugging

When setup fails:
1. run `python scripts/dev/doctor.py`;
2. correct the exact missing/mismatched runtime;
3. rerun bootstrap;
4. run fast gate;
5. use full gate before push.

No diagnostic command should request or print raw secrets.

## 9. Safety

Third-party developer tooling dependency added by P04-G: NONE  
Production infrastructure: NONE  
Production credentials/accounts: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 10. Next

After canonical closure:

`P04-H — Reproducible Build / Artifact Verification`

P04-H is not started by P04-G.

# FIN-P24-WZ-011 — subprocess output security boundary

Status: **review-required / not a release approval**. Applies only to developer tooling in `scripts/dev/common.py`; does not change trading permissions or frozen roadmap.

## Two distinct contracts

- `run_capture(argv)` captures stdout and stderr into memory and returns captured text on success. Callers must treat the returned text as **potentially sensitive** and must not print it or include it in public logs without a separately reviewed redaction policy. Its sanitized `ToolingError` on failure is not proof that a caller safely handles successful output.
- `run_live(argv)` deliberately **inherits** stdout and stderr. Child processes can print secrets directly into GitHub Actions logs before the wrapper raises a sanitized error. The wrapper **does not redact child output**. Use `run_live` only with commands whose entire output has been reviewed as safe for the target log audience; never pass tokens or credentials to an unreviewed child that may echo them.
- Neither wrapper uses a shell; both validate argv before spawning. Do not infer that this prevents leakage by an invoked executable.


## Call-site inventory (source inspection, 2026-11-24)

The following are the direct `run_live` calls in the inspected `scripts/dev/` Python entry points on PR HEAD `bb774c08d5617c5c7c90564379f74f42a7bdbf15`. This is **not** a repository-wide dynamic call graph or proof of safe log output.

| Caller | Child command | Output boundary / review action |
| --- | --- | --- |
| `bootstrap.py` | `corepack enable`; `corepack prepare pnpm@11.28.4 --activate` | Inherited package-manager diagnostics; review failure-path output and environment before use with credentials |
| `bootstrap.py` | `pnpm install --frozen-lockfile --ignore-scripts` | Inherited dependency-install output, including registry errors; review auth-bearing registry configuration and logs |
| `bootstrap.py` | `uv sync --locked --no-install-project` | Inherited dependency resolution/install diagnostics; review private index URLs and credential handling |
| `bootstrap.py` | `doctor.py --ci`; `local_gate.py fast`; optional `install_hooks.py [--force]` | Inherited nested tooling output; inspect nested commands, including all failure paths |
| `local_gate.py` | `doctor.py --ci`; `pnpm install --frozen-lockfile --ignore-scripts`; `uv sync --locked --no-install-project` (full mode) | Same inherited diagnostic exposure as bootstrap |
| `local_gate.py` | Governance, foundation CI lint/typecheck/unit/contract/security/promotion, config contract, unittest suites, supply-chain manifest, developer-tooling contract (fast mode) | Inherited test/check output; test failures can echo fixture data, environment or external CLI diagnostics |

`doctor.py` uses `run_capture` for version probes, not `run_live`; it subsequently prints collected version results. `install_hooks.py` invokes `subprocess.run` directly for Git hook-path discovery and is **outside** the `run_live` wrapper's guarantees. These observations do not certify either caller as safe.

**Risk disposition:** No call site above has been independently verified safe for every success/failure output path. Do not infer that `--ignore-scripts` prevents package-manager diagnostics from containing sensitive registry information. Keep this as an open security review item, rather than changing streaming behavior without an approved compatibility and redaction contract.

**Next bounded test:** exercise a synthetic child process locally with non-secret markers on stdout and stderr, both zero and nonzero exit codes, while capturing the *parent's* stdout/stderr at the process boundary. Assert the markers appear under the current `run_live` contract; do not print them into public CI logs. Any future redaction design requires a separate change, explicit size/encoding limits and independent review.

## Review and test checklist (pending independent A5/A8/A10 review)

1. Inventory every `run_live` call site and classify stdout/stderr for normal and failure paths, including third-party CLI diagnostics.
2. For any potentially sensitive output, avoid `run_live`; use a dedicated capture-and-redact implementation with a separately specified maximum output size, encoding, exit-code behavior, and tested redaction policy. Do **not** silently switch `run_live` to capture: existing callers may rely on streaming logs.
3. Regression-test the chosen implementation with a local synthetic child process emitting secret markers to both stdout and stderr and exiting nonzero; inspect **actual captured CI log bytes**, not just Python exception strings.
4. Re-run all mandatory checks on the exact final HEAD, obtain independent A5/A8/A10 reviews and exact-head Owner Gate, and respect protected-branch merge policy. This document is evidence of a known boundary, not remediation or authorization.

Live/Auto trading, financial transfers, and unapproved Demo orders remain disabled. No paid model endpoints or hosted agents are required.

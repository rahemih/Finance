# FIN-P24-WZ-011 — subprocess output security boundary

Status: **review-required / not a release approval**. Applies only to developer tooling in `scripts/dev/common.py`; does not change trading permissions or frozen roadmap.

## Two distinct contracts

- `run_capture(argv)` captures stdout and stderr into memory and returns captured text on success. Callers must treat the returned text as **potentially sensitive** and must not print it or include it in public logs without a separately reviewed redaction policy. Its sanitized `ToolingError` on failure is not proof that a caller safely handles successful output.
- `run_live(argv)` deliberately **inherits** stdout and stderr. Child processes can print secrets directly into GitHub Actions logs before the wrapper raises a sanitized error. The wrapper **does not redact child output**. Use `run_live` only with commands whose entire output has been reviewed as safe for the target log audience; never pass tokens or credentials to an unreviewed child that may echo them.
- Neither wrapper uses a shell; both validate argv before spawning. Do not infer that this prevents leakage by an invoked executable.

## Review and test checklist (pending independent A5/A8/A10 review)

1. Inventory every `run_live` call site and classify stdout/stderr for normal and failure paths, including third-party CLI diagnostics.
2. For any potentially sensitive output, avoid `run_live`; use a dedicated capture-and-redact implementation with a separately specified maximum output size, encoding, exit-code behavior, and tested redaction policy. Do **not** silently switch `run_live` to capture: existing callers may rely on streaming logs.
3. Regression-test the chosen implementation with a local synthetic child process emitting secret markers to both stdout and stderr and exiting nonzero; inspect **actual captured CI log bytes**, not just Python exception strings.
4. Re-run all mandatory checks on the exact final HEAD, obtain independent A5/A8/A10 reviews and exact-head Owner Gate, and respect protected-branch merge policy. This document is evidence of a known boundary, not remediation or authorization.

Live/Auto trading, financial transfers, and unapproved Demo orders remain disabled. No paid model endpoints or hosted agents are required.

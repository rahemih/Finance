# P24-WY-001 — Security postmerge evidence and Demo non-operational checkpoint

**Date:** 2026-11-04. **Scope:** evidence/status reconciliation only, not security certification or P24 closure.

## Confirmed repository facts

| Subject | Observed state | Evidence |
| --- | --- | --- |
| Historical PR #517 | MERGED at `bb33ffd8d25c941cd299878a5697a460d1b8df07`; postmerge Governance #41779026384 FAILED three times at Trivy installer before scan | [PR #517](https://github.com/rahemih/Finance/pull/517), [run #41779026384](https://github.com/rahemih/Finance/actions/runs/41779026384) |
| Security repair PR #521 | Owner exact HEAD `509a9bb81a908214746ace40e96c2b9f0533d05f`; SQUASH MERGED protected main at `5ac2a04dad1ce2d5603154bfc5b769da82c0beaa` | [PR #521](https://github.com/rahemih/Finance/pull/521) |
| PR #521 PREMERGE Governance | #41823248100 SUCCESS; 238 steps, 327 P24 tests and actual pinned Trivy OCI scan as recorded in PR evidence; premerge artifact SHA256 `3b2b700a8962a47f2a44ba395ded7498262ad29e6140b36cffa706aadeec050e` | [run #41823248100](https://github.com/rahemih/Finance/actions/runs/41823248100) |
| PR #521 POSTMERGE Governance + Branch Hygiene | **POSTMERGE_UNVERIFIED** in this checkpoint: available commit-status endpoint returned empty; associated-workflow connector only returns PR-triggered runs and returned no push runs. Neither proves success or failure. Do not mark PASS without exact SHA push-run evidence. | [commit](https://github.com/rahemih/Finance/commit/5ac2a04dad1ce2d5603154bfc5b769da82c0beaa), [Actions](https://github.com/rahemih/Finance/actions) |
| Incident #518 | GitHub issue state CLOSED at 2026-11-04T12:14:49Z; closing state is **not** a substitute for postmerge security CI evidence; historical failure remains unchanged | [#518](https://github.com/rahemih/Finance/issues/518) |
| Alternative PR #520 | CLOSED WITHOUT MERGE as superseded by approved merged #521; overlapping CI remediation must not merge again | [#520](https://github.com/rahemih/Finance/pull/520) |
| Operational trackers | Demo #508 OPEN; Live #491 OPEN | [#508](https://github.com/rahemih/Finance/issues/508), [#491](https://github.com/rahemih/Finance/issues/491) |

## Exact-main acceptance gate (pending independent verification)

1. Identify the *push-triggered* Governance Verify run whose `head_sha` is exactly `5ac2a04dad1ce2d5603154bfc5b769da82c0beaa`, not the premerge PR run.
2. Confirm completed/success for **all required** Governance jobs; actual immutable Trivy v0.75.0 ran `vuln,misconfig,secret` with HIGH/CRITICAL hard fail, valid `build/trivy.json`, SBOM and supply-chain evidence and unexpired foundation manifest.
3. Confirm separately exact-main Branch Hygiene completed/success, not merely that merged PR was mergeable.
4. Link run IDs, artifact ID and digest and reconcile incident #518 (currently closed) if evidence does not substantiate closure. Never rewrite historical PR #517 failure.
5. If any run is missing/failed/expired/inaccessible, retain **POSTMERGE_UNVERIFIED** (or FAILED if independently proven). No waiver or false pass.

## Demo and Live gate boundary

- Native MetaEditor build and execution of `P24ReadOnlyClockProbe.mq5` on *both independent Windows MT5 terminals* is NOT VERIFIED by CI. The broker raw tick UTC +~7200s anomaly is NOT attested. Never correct timestamps by subtracting 7200 automatically.
- Operational reconnect, quote-source rights, broker-authorized demo order lifecycle, ACK/idempotency and independent A5 veto are NOT VERIFIED. Synthetic offline fixture PASS != operational Demo PASS.
- P24-A is assessment-only CANONICAL_COMPLETE; P24-B BLOCKED, P24-C..I NOT_STARTED; nine PRE_FIRST_LIVE flags FALSE; FIRST_LIVE_OWNER_APPROVAL NOT_GRANTED, G13 NOT_STARTED, LIVE_TRADING DISABLED, AUTO_TRADING DISABLED.
- This checkpoint changes no broker orders, credential access, runtime state, risk policy or production configuration.

## Governed closeout

This is a **proposed PR** requiring exact-head Governance, A5/A8/A10 checks and independent Owner Human Gate before merge. A successful docs-only merge must itself have exact-main postmerge Governance + Branch Hygiene checked. It cannot make P24 canonical complete. Maintain #508 and #491 as OPEN.

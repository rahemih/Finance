# WEB-P0 P0-B Read-Only Monitoring Preview — DRAFT, not accepted

Task FIN-P23-WN-001. This draft stacks on unmerged [#504](https://github.com/rahemih/Finance/pull/504) which stacks on [#497](https://github.com/rahemih/Finance/pull/497). It is NOT eligible for merge until upstream exact-head Governance, independent security review and separate Human Gates are satisfied. No change to canonical main.

## Owner design reference consent — 2026-10-31

The Owner explicitly stated in this conversation that the reference images are approved. Source [native Google Doc](https://docs.google.com/document/d/19trhKWaIB9YUqc3h7sgrovKwRiJKFUM_RSjmj6NDPQ0/edit), revision captured in `apps/web/contracts/visual-reference-approval.json`; all **212 inline image IDs** matched across **34 PAGE records** with no missing, extra or duplicate IDs. This is **DESIGN_REFERENCE_APPROVED_IN_CONVERSATION**, not a frozen reproducible image baseline: source image bytes/SHA-256, owner per-revision acceptance, viewport browser rendering and Playwright pixel comparison are NOT_RUN/PENDING. Existing main source manifest `ownerApprovedBaselineCount=0` remains unchanged intentionally pending asset capture and hash validation. Implemented browser output is not automatically accepted.

## Initial implementation, only three P0-B pages

| PAGE | Route | Document-backed structural components | Reference images |
|---|---|---|---|
| 010 Dashboard | `/dashboard` | status banner, KPI shell, market/opportunity, risk, health/alerts, RTL navigation | 7 |
| 079 System Health | `/system` | full-width highest-risk banner, provider/heartbeat list, incident evidence absence | 7 |
| 084 Notification Center | `/system/alerts` | severity states, list/detail grid, no false zero alarm count | 6 |

Backend reads `/api/v1/dashboard/overview`, `/api/v1/ops/health/summary`, `/api/v1/notifications/in-app` remain **PROPOSED/NOT_CONNECTED**. No mocked real portfolio, prices, health flags or alerts. Unknown data is displayed as unknown, not zero or NORMAL. All actions that would require sessions, CSRF, permissions, Risk override, notification ACK or execution are absent. Internal links only among verified preview routes.

## Evidence required

- Exact pin/frozen install, TS and Next Build, HTTP 200 for each preview, 404 for dangerous API and disabled login route, explicit preview/warning/noindex, HTTP denied POST.
- Separate static tests for 34 page manifest, 212 native image IDs, 20 monitoring-page image counts, state/permission invariants and 1440/768/360 responsive contracts.
- Source Security / Auth / CORS / Cross-user / P04 license checks, Playwright screenshot comparison, accessibility and owner implementation review still required; no UI ACCEPTED or production release claim.
- P04 fail-closed license Governance currently unresolved and inherited from #504. A5/P16, P24-B/G13, LIVE/AUTO disabled and no account/market/order APIs.

## Owner gates

1. Review each implemented page at browser widths 1440/768/360 against the owner-approved 7+7+6 references and capture exact image hashes.
2. Independently review security and resolve P04 compliance without waivers/fake reviewers.
3. #497 then #504 need individually approved/merged and verified before this stacked PR may retarget main and receive its own explicit SHA+artifact Human Gate.

## Unapproved first-run browser capture evidence (planned)

The Draft runtime job now launches the built Next server and preinstalled Google Chrome headless to capture **nine actual source UI images** at 1440, 768 and 360 px for PAGE-010, PAGE-079 and PAGE-084. Each PNG gets SHA256 and a manifest, uploaded as a short-lived GitHub Actions artifact. This is **candidate output** only; the Owner's 212 native Google Doc reference images remain DESIGN_APPROVED, while screenshot equivalence, responsive geometry and browser baseline acceptance remain NOT_RUN until actual comparison. The CI job must finish before anyone claims browser screenshots exist.

## Browser QA checkpoint — first screenshot run 41214435404

Nine PNG viewport captures were created (1440, 768, 360 for three pages), and visual review detected a **real** clipped/compressed critical-warning badge. The subsequent CSS revision applies non-shrinking desktop badges and a distinct full-row mobile badge. The original screenshots are diagnostic evidence only. A new full Build, HTTP and Chrome capture must pass on the updated head; neither the old nor replacement images are declared matched to the Owner's reference baseline.

## Second screenshot QA defect

A second visual review of the corrected 9-image output found that the generic direct-child CSS selector styled *both* the exclamation icon and the adjacent warning Tag as 28x28 circles. Root cause: `.nq-mon-critical>span` instead of `.nq-mon-critical>span:first-child`. Corrected icon-only selector and added regression test. A fresh CI screenshot pass must succeed on this new SHA; previous images are diagnostic, not accepted baselines.

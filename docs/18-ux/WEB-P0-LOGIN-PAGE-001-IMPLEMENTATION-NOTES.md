# WEB-P0 — PAGE-001 Login implementation checkpoint (SOURCE DRAFT, NOT ACCEPTED)

Task: `FIN-P23-WK-001` — separate non-live PAGE-001 package.
Branch: `feat/FIN-P23-WK-001-web-p0-login-source` (created from canonical main).
Depends on **PR #496 (contract)** and **PR #497 (Next App Router foundation)** completing independent reviews, owner Human Gates, canonical merge and postmerge evidence. This PR must not merge ahead of them.

## Implemented source
- Route `/auth/login`, source-only non-operational React view and responsive CSS based on exact PAGE-001 tables and UI-001..UI-012.
- Persian copy from COPY-001..023, with fail-visible unavailable message; no credentials accepted in this draft.
- Canonical P23-B CSS variables, RTL shell, Noto Sans Arabic/Noto Sans intentions, 44px targets and 360/768/1024/1440 planned responsive behavior.
- Eight typed primary visual states and ten documentary screenshot IDs, bound to the exact Google Docs native inline object references in `apps/web/contracts/login-visual-scenarios.json`; SHA-256 and baseline files remain null until trusted extraction/approval.
- User visual feedback recorded for scenarios 001-04/001-05, but ALL ten scenarios remain REVIEW_REQUIRED until owner-approved baseline with real hashes and browser regression.
- Password and identifier fields, Login button and Passkey disabled by design. Form preventDefault, no identity or session API, credential collection, cookies, local storage, telemetry or real authentication. Dark/Light theme toggle is cosmetic only.

## Not done / must NOT claim
- No runnable web package in this branch until foundation PR #497 and separately reviewed version/lockfile ADR.
- No real Auth BFF/IdP, session, MFA, device flow, WebAuthn, recovery, RBAC enforcement or API integration.
- No TypeScript/Next bundle build, Playwright screenshot matching, axe WCAG/manual screen-reader, mobile browser, security end-to-end or API contract PASS.
- Static Python and Node source contract checks are only preliminary; passing them does not certify security/visual readiness.

### Gates
1. #496 independent review + Owner Human Gate + merge + evidence.
2. #497 independent review + Owner Human Gate + merge + pinned runtime ADR.
3. Auth identity/session/BFF/CSRF/role/domain/permission ADR approval.
4. 10 owner baseline screenshots approved and versioned with checksums.
5. Pinned runtime builds plus full 10-scenario visual, a11y, security and E2E evidence; then page-specific Owner acceptance.
6. Independent LIVE/P24-B/G13 remain blocked and unrelated.

Rollback: close Draft PR and abandon this isolated branch; `main` remains unchanged.

## Runnable non-operational preview integration checkpoint (2026-10-31)

This work is staged on top of unmerged #504 runtime, which itself is based on unmerged #497. Order for future governance: #497 → #504 → #498, each with independent scope/security reviews and Owner gates. The runtime is pinned and builds but its P04 license Governance remains FAIL; this preview cannot be merged or deployed as a substitute for license compliance, real Auth, visual baselines, or independent reviews. Actual Next/TS and HTTP smoke will run in the latest login source CI; do not claim PASS until run completes.

Once stacked, GET `/auth/login` may render a visibly disabled preview with HTTP 200, **not** an operational authentication service. This branch alone changes the parent runtime smoke expected login response to 200 while requiring disabled fields, a denied POST and denied dashboard/orders APIs. Such source-preview evidence is separate from 10 screenshot matching, authentic identity/session services and all 34 WEB-P0 page acceptance gates.

## Source branch replay onto pruned runtime

The original login preview was replayed onto the latest still-DRAFT runtime PR #504 Head `70b998eb58fd77ddc56b7a14cb9a98e820336ba0`; it inherits the TypeScript 5.9.3/Sharp-pruned pnpm lock, React/Next version pins and P04 fail-closed controls. No prior approved visual baseline and no production Auth. Verify latest exact-head Login/Runtime/Source/Governance checks separately before any merge.

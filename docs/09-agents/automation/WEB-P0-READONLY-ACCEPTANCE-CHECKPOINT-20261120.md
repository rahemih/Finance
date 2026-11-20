# WEB-P0 read-only acceptance checkpoint (2026-11-20)

Status: **PROPOSED / NOT ACCEPTED / NOT MERGED**. This document is an engineering checklist, not a waiver, independent review, or approval to deploy.

## Canonical baseline and existing work
- Base main: `9c26afc90c0415f5cf2e3ddc4f2f9cd8bb42d2fe` (reverify before merging).
- Existing stacked draft implementation: #507 (dashboard, system, alerts), #509 (markets, watchlist, asset), #512 (login); **do not duplicate or merge out of order**.
- Original owner-approved visual authority: embedded images in the Google Doc linked in #509. Browser screenshots are evidence, not approved replacements.
- Blocking supply-chain/license case: #530 and #505; `caniuse-lite` CC-BY-4.0 requires independent disposition, not a blanket allow-list change.

## Next executable slice: PAGE-011 /markets (read-only)
1. Work on the existing #509 branch only after checking its current head and parent stack; do not alter canonical main directly.
2. Keep missing/unknown price, volume, timestamp, source, and quality **unknown**, never synthesize live data or display a green healthy state for missing evidence.
3. Deny POST/PUT/PATCH/DELETE with 405; retain read-only preview/noindex behavior and no credentials, orders, broker calls, transfers, or trading controls.
4. Add source tests for unavailable quote, stale timestamp, unverified source, empty vs not-loaded watchlist, and denied unsafe HTTP methods. Require latest-head Next build, TypeScript, source tests, and browser 1440/768/360 screenshots.
5. Compare screenshot pixels against the **same owner-approved original image** with reproducible provenance. Prior #509 diagnostic desktop mismatch: PAGE-011 15.943%, PAGE-015 17.056%, PAGE-019 14.169% against <=0.5% target; these are not formal SSIM acceptance.
6. Record exact PR head, workflow run IDs, screenshot artifact IDs/hashes, and mismatch calculation. Do not mark visual acceptance without owner review of rendered output.

## Non-negotiable gates
- P04 SBOM/license Governance must pass without waiver; independent reviewer must evaluate license and attribution.
- Independent A5/A8/A10 decisions and PR-specific exact-head Human Gate; branch protection and required CI stay intact.
- No Live/Auto or demo orders without a separate governing authorization.
- WEB-P0 and P00–P24 remain incomplete until their own evidenced acceptance; this document is not a completion declaration.

## Evidence references
- https://github.com/rahemih/Finance/pull/507
- https://github.com/rahemih/Finance/pull/509
- https://github.com/rahemih/Finance/pull/512
- https://github.com/rahemih/Finance/issues/530
- https://github.com/rahemih/Finance/pull/505

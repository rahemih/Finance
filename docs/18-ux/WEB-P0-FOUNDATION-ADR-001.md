# WEB-P0-ADR-001 — Code-first foundation boundary (PROPOSED, NOT ACCEPTED)

Task: FIN-P23-WJ-001 (post-P23 reference extension; distinct from the formal P23 E2E closure)
Owner direction: 2026-10-31, non-live implementation only.
Depends on contract PR #496 (Draft, not merged at foundation creation).

## Recorded facts
- P23-A route roots are canonical in `config/ux/information-architecture.json`. Detailed 34 WEB-P0 routes are proposed by the Google Doc.
- P23-B token sources: `config/ux/design-system.json`. RTL fa-IR, financial LTR islands, Noto Sans Arabic/Noto Sans intended.
- WEB-P0: 8 security, 3 monitoring, 10 market, 4 signals, 8 trade/risk, 1 demo = 34 pages; 212 screenshot inventory.
- The source Google Doc is DRAFT v0.8 and owner reviews for screenshot baselines are incomplete. Pixel regression NOT_RUN.
- P24-B and G13 block any live/auto authorization.

## Accepted for safe draft staging (not a deploy decision)
1. Commit source-only `apps/web/src/app/layout.tsx`, token CSS and headless registry; **no page implementation**.
2. Treat every proposed detail route as an inventory item until route/contract approval; no active route or fake backend.
3. Deny browser trading authority; Auth, OMS, Risk Veto, BFF and credential handling are absent, not simulated as secure.
4. Keep PR Draft and all merges gated, including this PR and #496.

## OPEN — separate review / ADR before runnable build
- Fix exact Next.js/React/TypeScript and Test/Playwright package versions and compatible Node/pnpm, lockfile, licenses, SBOM and CVE checks.
- Decide server-side BFF Route Handlers/Gateway; authenticated cookie/session and CSRF/RBAC; OpenAPI/JSON Schema and generated types.
- Pin browser/OS/fonts/DPR and collect owner-approved screenshot files + SHA-256, fixtures and manifest for all 212.
- Define safe navigation and no-render behavior for pending 34 pages and WEB-P1/P2.
- Establish reproducible Build/Lint/TypeScript/Unit/Component/E2E/Visual/Accessibility/Security checks.

Disposition: **PARTIAL FOUNDATION ONLY / NO SCREEN IMPLEMENTED / NO APPROVED BASELINE / NO PROD AUTHORITY**.

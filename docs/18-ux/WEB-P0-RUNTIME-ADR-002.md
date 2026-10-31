# WEB-P0 Runtime ADR-002 — Pinned, non-live browser build (PROPOSED)

Status: **DRAFT / NOT_APPROVED / NOT_MERGED**. Governed task FIN-P23-WL-001, stacked on #497, with #498 login source separately gated.

## Proposed exact versions

- Node.js 24.21.0, pnpm 11.28.4 (canonical root).
- Next.js **16.4.3** (patched release following October 14, 2026 advisories; do not use affected pre-16.4.1), React/React-DOM **19.3.1**, TypeScript **7.0.2**.
- @types/react and @types/react-dom **19.3.0**; @types/node **24.19.2**.
- All version specifiers exact; install scripts disabled for lock generation. No experimental/canary dependencies or CDN fonts.
- Open-source dependencies require machine-verified SBOM, license, vulnerability scan and approval before promotion; no claim that advisories are fully reviewed yet.

## Non-operational proof surface

Root `/` is a clearly labeled **build-only sentinel**; it is NOT WEB-P0 PAGE-001 or an accepted screen. 34 proposed routes remain unimplemented and owner baseline review remains mandatory for 212 scenarios. No Auth, cookie, API, provider, BFF, trade execution, risk override, deployment, mock financial data or browser persistence. Do not publish this build probe as production UI.

## Reproducibility / staged process

1. CI generates a pnpm v11 lock with `--lockfile-only --ignore-scripts`, logs it as immutable evidence; exact lock must be committed to repository by a governed git change. No direct `main` edit.
2. Replace preparation job with a strict `--frozen-lockfile --ignore-scripts` install, real Next build, TypeScript typecheck and source/safety tests; confirm GitHub evidence on final SHA.
3. Additional browser accessibility, image/visual matching, security API and Auth tests are **NOT_RUN** until those capabilities exist. For any install without lifecycle scripts, SWC availability must be checked through real build result, not inferred.
4. Formal ADR/security review and separate Owner Human Gate remain mandatory; #497 must merge before this stacked PR becomes eligible for merge.

No LIVE_TRADING, AUTO_TRADING, or broker operations; P24-B, G13, A5 risk veto and P16 firewall unchanged.

## Verified checkpoint (2026-10-31, before this follow-up change)

- GitHub next build / TypeScript / frozen install / source checks / high+ audit all SUCCESS on head `0e5e56d79602d73954000efa9c11579ee2299061`, run `41189528333`.
- Actual pnpm lock generated in isolated GitHub Actions `41189453933`, committed verbatim to the PR by a second governed SHA, and installed with `--frozen-lockfile --ignore-scripts`.
- Next guard is non-functional `/` only. This follow-up adds noindex, conservative response headers and HTTP smoke tests to ensure `/auth/login`, `/dashboard`, `/api/v1/orders` return 404 until separately approved implementations. Every new head MUST rerun CI; no inherited PASS.
- No browser Playwright, axe, screen reader, user-approved screenshot baselines, Auth security, session, BFF, or production acceptance yet.

## Dependency reduction adopted into this still-unmerged draft — 2026-10-31

Scoped dependency pruning evidence originates in [experiment PR #506](https://github.com/rahemih/Finance/pull/506) and official GitHub-generated pnpm lock [run 41200976897](https://github.com/rahemih/Finance/actions/runs/41200976897). `apps/web/package.json` now pins TypeScript **5.9.3** (classic JS compiler); `pnpm-workspace.yaml` excludes only optional `sharp` and `@img/sharp*` packages. Original `next.config.ts` already sets `images.unoptimized=true`. The patch **retains** Next.js 16.4.3 and native SWC; it does not remove or override compiler required by Next.

On experiment head `c288e915c3232309f4665fa4934cc80eba8ad528`: frozen Next build+HTTP+source/security+audit [41201096035](https://github.com/rahemih/Finance/actions/runs/41201096035), dedicated prune check [41201096305](https://github.com/rahemih/Finance/actions/runs/41201096305) and Foundation source [41201096026](https://github.com/rahemih/Finance/actions/runs/41201096026) all **SUCCESS**. Mandatory Governance [41201096274](https://github.com/rahemih/Finance/actions/runs/41201096274) still **FAIL** at SBOM license gate, with missing component count reduced **88 → 31** (29 npm, 2 temporary experimental action SHA records), and **zero Go or Sharp/libvips components**. Source package TypeScript@5.9.3 declared Apache-2.0 at official npm registry in [run 41201334936](https://github.com/rahemih/Finance/actions/runs/41201334936).

The latest exact head of this PR requires **fresh** Frozen Build, TypeScript, smoke, Governance and SBOM checks; previous passes are historical evidence only. The nonessential dependency elimination does **NOT** authorize blind P04 license review (including `caniuse-lite` CC-BY), bypass, waiver, publishing, auto-merge, or Auth/trading.

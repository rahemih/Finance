# NEXUS QUANT — WEB-P0 scaffold (DRAFT, NOT RUNNABLE YET)

This folder starts the user-authorized **non-live** React/Next.js/TypeScript implementation track with a code-first App Router layout, 34-page route inventory, canonical P23 token bridge and safety constants. It contains **no implemented WEB-P0 visual page** and does not provide a browser entry point.

- The manifest's 34 routes are **PROPOSED** (P23's 11 canonical surfaces remain authoritative); the 212 screenshots are **inventory only**, not asset checksums or approved baselines.
- This checkpoint deliberately has **no package.json or new dependencies**. Next/React/TypeScript exact versions, license/CVE/SBOM, Node 24.21.0 + pnpm 11.28.4 lockfile, auth/BFF decisions and ADR approval are prerequisites to the runnable package checkpoint.
- CSS maps only the **verified P23-B canonical tokens**; it is not a redesign or screenshot match. No third-party CDN fonts.
- All application routes, backend calls, mock financial values, cookies, API proxies, and trading actions are absent.
- Tests: `python3 -m unittest discover -s tests/web_p0 -p 'test_*.py' -v`. They check registry/token/security invariants only. They do **not** prove Build, TypeScript, visual fidelity, accessibility or E2E.
- PR #496 contract, independent review, owner Human Gate and approved screenshot baselines remain unresolved prerequisites. **Do not merge or deploy** this draft without separate governance.

Source: https://docs.google.com/document/d/19trhKWaIB9YUqc3h7sgrovKwRiJKFUM_RSjmj6NDPQ0/edit

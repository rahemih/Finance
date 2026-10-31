# WEB-P0 Dependency Pruning Experiment — FIN-P23-WM-001

**Status:** DRAFT / NO MERGE / no production effect. Based on [PR #504](https://github.com/rahemih/Finance/pull/504), which itself is stacked on unmerged #497.

The license/SBOM fail on runtime #504 included 88 missing license components: 79 npm (including 14 LGPL-composite Sharp/libvips and one CC-BY caniuse-lite) and nine TypeScript-go toolchain Go modules. This experiment is a **dependency elimination** first, not a legal/policy workaround.

- TypeScript 7.0.2 native/Go build is replaced provisionally with TypeScript 5.9.3 (JavaScript implementation); must preserve exact TypeScript and real Next.js build behavior.
- Next.js 16.4.3 and React 19.3.1 remain. Next's native `@next/swc-*` is preserved. Only optional Sharp/libvips image optimization is targeted for exclusion; `images.unoptimized = true` already enabled and no image processor is exposed in the build-only sentinel.
- `ignoredOptionalDependencies` is a pnpm feature. Whether it prunes **lockfile SBOM entries** as well as actual installation must be established by generated lockfile + Syft results; no assumption of guaranteed compliance.
- P04 allow/review/block sets and waivers are completely unchanged.
- The experiment remains blocked if Next build, TypeScript, security checks, source invariants or SBOM-license validation fail. The caniuse-lite CC BY obligation may remain and cannot be ignored or relabeled.
- Any success here must be applied to #504 only after clean CI, security/license assessment and separate owner gate; do not merge this branch ahead of canonical dependencies.

**Next:** generate real pnpm lock from CI, commit unchanged bytes with readback hash, run real Build, TypeScript, HTTP, Governance, compare residual package counts.

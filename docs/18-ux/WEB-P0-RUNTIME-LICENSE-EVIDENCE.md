# WEB-P0 — Runtime third-party license evidence (OPEN / BLOCKED)

Task `FIN-P23-WL-001`; PR [#504](https://github.com/rahemih/Finance/pull/504) stacked on unmerged #497. Do not merge or deploy.
Canonical rules: `config/supply-chain/license-policy.json`, `scripts/ci/supply_chain_policy.py`. No waived or bypassed rule.

## Root cause and immutable evidence

- Governance [41189654816](https://github.com/rahemih/Finance/actions/runs/41189654816) FAILED at **Validate SBOM / license policy**; Syft CycloneDX 1.7 returned **88 package components without explicit license**. This is a **hard gate**.
- A source-only collector subsequently fetched exact **79 npm package/version** license declarations from the approved `registry.npmjs.org` and recorded the source URI and tarball SRI integrity, via [run 41189938730](https://github.com/rahemih/Finance/actions/runs/41189938730).
- **64/79 npm** report licenses in the current policy's allow classes: MIT 24, Apache-2.0 36, ISC 2, BSD-3-Clause 1, 0BSD 1. These are unapproved **candidate assertions** until checked against package files and committed through independent governance.
- **14/79 npm** report LGPL-3.0-or-later or composite expressions that include it, requiring explicit legal/distribution and policy review (not allowed by an automatic assertion).
- **1/79 npm** (`caniuse-lite@1.0.30001820`) declares `CC-BY-4.0`, currently **unclassified** and requiring policy/legal assessment.
- **9 Go module purls** (transitively from TypeScript-go) still lack verified, exact-version license evidence. No license identity has been fabricated.

## npm instances requiring active assessment

- `@img/sharp-libvips-darwin-arm64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-darwin-arm64/1.3.4
- `@img/sharp-libvips-darwin-x64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-darwin-x64/1.3.4
- `@img/sharp-libvips-linux-arm64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-arm64/1.3.4
- `@img/sharp-libvips-linux-arm@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-arm/1.3.4
- `@img/sharp-libvips-linux-ppc64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-ppc64/1.3.4
- `@img/sharp-libvips-linux-riscv64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-riscv64/1.3.4
- `@img/sharp-libvips-linux-s390x@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-s390x/1.3.4
- `@img/sharp-libvips-linux-x64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linux-x64/1.3.4
- `@img/sharp-libvips-linuxmusl-arm64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linuxmusl-arm64/1.3.4
- `@img/sharp-libvips-linuxmusl-x64@1.3.4`: `LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-libvips-linuxmusl-x64/1.3.4
- `@img/sharp-wasm32@0.35.5`: `Apache-2.0 AND LGPL-3.0-or-later AND MIT` — https://registry.npmjs.org/%40img%2Fsharp-wasm32/0.35.5
- `@img/sharp-win32-arm64@0.35.5`: `Apache-2.0 AND LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-win32-arm64/0.35.5
- `@img/sharp-win32-ia32@0.35.5`: `Apache-2.0 AND LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-win32-ia32/0.35.5
- `@img/sharp-win32-x64@0.35.5`: `Apache-2.0 AND LGPL-3.0-or-later` — https://registry.npmjs.org/%40img%2Fsharp-win32-x64/0.35.5
- `caniuse-lite@1.0.30001820`: `CC-BY-4.0` — https://registry.npmjs.org/caniuse-lite/1.0.30001820

## Go license texts checked against tagged/commit-pinned upstream repositories (evidence, not approval)

- `pkg:golang/github.com/go-json-experiment/json@v0.0.0-20260623181947-01eb4420fa68`: upstream LICENSE is `BSD-3-Clause`, source https://raw.githubusercontent.com/go-json-experiment/json/01eb4420fa68/LICENSE; distribution/NOTICE review pending
- `pkg:golang/github.com/klauspost/cpuid/v2@v2.2.10`: upstream LICENSE is `MIT`, source https://raw.githubusercontent.com/klauspost/cpuid/v2.2.10/LICENSE; distribution/NOTICE review pending
- `pkg:golang/github.com/mackerelio/go-osstat@v0.2.7`: upstream LICENSE is `Apache-2.0`, source https://raw.githubusercontent.com/mackerelio/go-osstat/v0.2.7/LICENSE.txt; distribution/NOTICE review pending
- `pkg:golang/github.com/microsoft/typescript-go@v0.0.0-20260708042240-2bd066d87f5b%2Bdirty`: upstream LICENSE is `Apache-2.0`, source https://raw.githubusercontent.com/microsoft/typescript-go/2bd066d87f5b/LICENSE; binary build provenance STILL UNVERIFIED (`+dirty` suffix)
- `pkg:golang/github.com/zeebo/xxh3@v1.1.0`: upstream LICENSE is `BSD-2-Clause`, source https://raw.githubusercontent.com/zeebo/xxh3/v1.1.0/LICENSE; distribution/NOTICE review pending
- `pkg:golang/golang.org/x/sync@v0.21.0`: upstream LICENSE is `BSD-3-Clause`, source https://raw.githubusercontent.com/golang/sync/v0.21.0/LICENSE; distribution/NOTICE review pending
- `pkg:golang/golang.org/x/sys@v0.46.0`: upstream LICENSE is `BSD-3-Clause`, source https://raw.githubusercontent.com/golang/sys/v0.46.0/LICENSE; distribution/NOTICE review pending
- `pkg:golang/golang.org/x/term@v0.44.0`: upstream LICENSE is `BSD-3-Clause`, source https://raw.githubusercontent.com/golang/term/v0.44.0/LICENSE; distribution/NOTICE review pending
- `pkg:golang/golang.org/x/text@v0.38.0`: upstream LICENSE is `BSD-3-Clause`, source https://raw.githubusercontent.com/golang/text/v0.38.0/LICENSE; distribution/NOTICE review pending

**Caution:** these are repository-license observations at named refs, **not** a cryptographic match of the source inside the distributed TypeScript binary. Separate independent license/security review and provenance checks remain mandatory.

## Next allowed remediation (not yet performed)

1. Validate registry assertions independently, inspect relevant LICENSE/NOTICE files and redistribution obligations, and document legal/security decision for LGPL/composite and CC-BY-4.0.
2. Verify exact Go module upstream licenses against the pinned revisions and compare with SBOM components.
3. Under a **separately governed P04 security-policy task and explicit approval**, add only evidenced, exact-version curated assertions already supported by current license-policy schema; review-class items require explicit license-review waivers if policy allows, with independent security/legal signoff. **Do not auto-waive or silently extend policy allow-list.**
4. Rerun required Governance on final exact SHA; until that test passes, #504 stays DRAFT/BLOCKED. Root Next build, TypeScript, HTTP smoke and high+ npm audit passing does NOT resolve license gate.
5. Separate #497 and #504 owner Human Gates, source/security review, #498 authentication baseline approvals and all P24/G13 restrictions stay in force.

This is dependency evidence, not a legal conclusion, signed reviewer approval, or a claim that distribution is authorized.

## Pruned runtime follow-up / measured residual — 2026-10-31

This file's original 88/79/9 inventory documents the historical TypeScript 7 / Sharp runtime, **not the current pruned proposal**. The new pnpm lock excludes all Sharp/libvips optional and TS7 native Go packages while preserving `@next/swc-*`. Verified experimental Syft P04 failure 41201096274 listed **31 missing** (29 npm + two experiment-workflow GitHub action SHAs). License controls remain FAIL CLOSED.

Current proposal [P04 #505](https://github.com/rahemih/Finance/pull/505) was narrowed to **28 needed exact package license assertions**, of which 27 were already sourced in PR #504's original 79 npm registry results and one is new TypeScript@5.9.3 Apache-2.0. `caniuse-lite@1.0.30001820` CC-BY-4.0 remains unresolved, plus any new Syft metadata warnings. Neither #505 nor runtime #504 is merged or independently security-reviewed. Do not grant additional license assertions for removed packages.

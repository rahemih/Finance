# P04-F targeted exact license assertion review (DRAFT / NOT ACCEPTED)

Task `FIN-P04-WF-001-R01`, [PR #505](https://github.com/rahemih/Finance/pull/505) — **OPEN, UNMERGED**; original proposal reduced to 28 exact-version sources after removing redundant packages on experimental [PR #506](https://github.com/rahemih/Finance/pull/506).

## Narrowed proposal grounded in the latest experimental SBOM

- Initial Next runtime #504 had 88 missing-license components (79 npm + 9 Go). Dependency pruning PR #506 replaces native TypeScript 7 with TypeScript 5.9.3 (exact) and omits optional Sharp/libvips, leaving SWC intact. Both real Next/TypeScript Build and HTTP smoke PASS on #506.
- [Governance run 41201096274](https://github.com/rahemih/Finance/actions/runs/41201096274) on experiment exact head `c288e915c3232309f4665fa4934cc80eba8ad528` still correctly **FAILED** SBOM license policy: 31 missing entries, 29 npm + 2 GitHub Actions pinned by SHA. No Go or Sharp/libvips entries remain.
- 27 of those 29 npm entries were previously fetched from npm exact-version metadata (PR #504 source research [run 41189938730](https://github.com/rahemih/Finance/actions/runs/41189938730)) and have license within canonical P04 allow classes.
- Additional TypeScript `5.9.3` exact-version npm metadata, including SHA512 tarball SRI, was captured in [run 41201334936](https://github.com/rahemih/Finance/actions/runs/41201334936), job `124537580901`, under `https://registry.npmjs.org/typescript/5.9.3`, license `Apache-2.0`.
- Thus **only 28 source-specific curated assertions are PROPOSED**, rather than 72. Original 14 LGPL/composite Sharp/libvips package and 9 TypeScript-go module assertions are withdrawn from this proposal because those dependencies are no longer present in the pruned lockfile; do not grant unnecessary P04 policy exceptions.
- Remaining `caniuse-lite@1.0.30001820` is required transitively by Next; current npm metadata says `CC-BY-4.0`, not in allow/review P04 classes. This case is **UNRESOLVED** and needs separate independent legal/license assessment and any explicit governed policy decision. No silent reclassification.
- The 2 GitHub Actions SHA purls appeared in this experiment's custom CI workflow and are being reevaluated with existing canonical pinned-version annotations; do not assert their license from SHA alone or change P04 allow classes.
- No waiver added; `config/supply-chain/waivers.json`, `.trivyignore` and GitHub Governance remain unchanged. **Even if this PR merges after security review and owner approval, #504/#506 may still FAIL until CC-BY and any residual PURL provenance are addressed.**

## Mandatory approvals and verification

1. Independently compare the 28 exact purls, versions, SPDX declarations, tarball SRI and upstream LICENSE/NOTICE text; verify P04 curated-assertion semantics and whether distribution obligations are met.
2. Run the required Governance check on exact PR #505 head; absence of a failure does not grant a license review approval.
3. Obtain qualified independent supply-chain/security reviewer approval and exact-head/manifest Owner Human Gate for PR #505 before any merge.
4. No app/runtime release, credential entry, broker, trading, LIVE/AUTO or external deployment authorization from these document-only changes.

## Independent license-review checklist — supporting public terms (not a signed review)

- For the `@img/sharp-libvips-*` binary packages, validate the exact v1.3.4 distribution/NOTICE contents and LGPL-3.0-or-later composite expressions. The upstream sharp-libvips repository identifies LGPLv3 components and their third-party notices; record whether this project is hosted only or distributes binary artifacts. References: https://github.com/lovell/sharp-libvips/blob/main/THIRD-PARTY-NOTICES.md and https://www.libvips.org/. This note is not a conclusion that all v1.3.4 binary obligations are met.
- For `caniuse-lite@1.0.30001820` (`CC-BY-4.0`), an independent reviewer must establish the originator's required credit, license link, modification statement and distribution context. Official text: https://creativecommons.org/licenses/by/4.0/legalcode. **Do not auto-add CC-BY to the P04 allow list.**
- For `typescript-go` reported `+dirty`, verify distributed binary/build provenance and embedded source license/NOTICE separately; an upstream LICENSE alone cannot attest to the binary.
- Capture reviewer identity and timestamp, license text hashes for actual distributed versions, redistribution or hosted-only decision, proof of source/NOTICE availability, and every exception/waiver before marking accepted.
- No formal legal opinion or second-party independent review has been obtained; `REVIEW_REQUIRED` remains in effect.

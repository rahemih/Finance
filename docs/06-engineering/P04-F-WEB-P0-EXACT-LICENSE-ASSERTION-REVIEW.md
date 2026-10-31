# P04-F repair — WEB-P0 source-backed exact license assertions (DRAFT / SECURITY REVIEW REQUIRED)

**Task:** FIN-P04-WF-001-R01, proposed PR on main, independent security & Owner Human Gates PENDING.
**Source:** [WEB-P0 runtime draft #504](https://github.com/rahemih/Finance/pull/504), official [registry evidence CI run 41189938730](https://github.com/rahemih/Finance/actions/runs/41189938730), original failure [41189654816](https://github.com/rahemih/Finance/actions/runs/41189654816).

## Bounded proposed change

This PR adds **72 individually pinned source-backed curated assertions** to the *existing* `config/supply-chain/license-policy.json` mechanism; no validation code, allow/review/block lists or waivers are changed.

- 64 npm exact package/version identities report license `MIT` / `Apache-2.0` / `BSD-3-Clause` / `ISC` / `0BSD` from official npm registry package metadata. Each record holds the registry URL and tarball SRI for provenance.
- Eight Go exact module/version identities have upstream repository LICENSE text inspected at their tag/commit and mapped to `MIT`, `BSD-2-Clause`, `BSD-3-Clause`, or `Apache-2.0` with pinned source URL.
- Existing P04 curated-assertion implementation, not a new validation bypass, is reused. These claims still require independent verification and human acceptance before this proposal may merge.

## Deliberately unresolved and blocked

- 14 LGPL-3.0-or-later/composite npm components. Policy `LICENSE_REVIEW` remains obligatory; no waiver requested or signed.
- One `caniuse-lite@1.0.30001820` declares CC-BY-4.0, not present in current P04 allow/review lists; requires explicit obligations/policy review.
- `pkg:golang/github.com/microsoft/typescript-go@v0.0.0-20260708042240-2bd066d87f5b%2Bdirty` upstream Apache-2.0 LICENSE was found but source-to-distributed-binary identity/attestation is not verified; purposely **excluded** from assertions.
- Therefore even merging this PR would **not** mean PR #504 passes Governance or may be merged. The compliance gate remains fail-closed until the remaining cases are resolved separately.

## Evidence integrity / security

Each curated identity_prefix is the complete `pkg:` URL at its exact version, preventing wildcard grants to future revisions. Use the official pinned registries and upstream license texts to independently confirm all 72 claims. Dist.integrity is recorded, not substituted for a full tarball license/NOTICE audit.

Reviewers must check source integrity, SPDX legal obligations, NOTICE distribution, and whether an accepted license assertion is compatible with the frozen P04 security/governance policy. The proposal is **not** a declaration of legal compliance and does not grant permission to ship/deploy.

## Safety and workflow

No source/runtime/account/Live/Auto-trading change, no independent A5 risk veto or P16 firewall modification, no visual baseline approval, and no actions on protected `main` from this draft. If Owner declines review, close the PR and retain current policy.


## Independent license-review checklist — supporting public terms (not a signed review)

- For the `@img/sharp-libvips-*` binary packages, validate the exact v1.3.4 distribution/NOTICE contents and LGPL-3.0-or-later composite expressions. The upstream sharp-libvips repository identifies LGPLv3 components and their third-party notices; record whether this project is hosted only or distributes binary artifacts. References: https://github.com/lovell/sharp-libvips/blob/main/THIRD-PARTY-NOTICES.md and https://www.libvips.org/. This note is not a conclusion that all v1.3.4 binary obligations are met.
- For `caniuse-lite@1.0.30001820` (`CC-BY-4.0`), an independent reviewer must establish the originator's required credit, license link, modification statement and distribution context. Official text: https://creativecommons.org/licenses/by/4.0/legalcode. **Do not auto-add CC-BY to the P04 allow list.**
- For `typescript-go` reported `+dirty`, verify distributed binary/build provenance and embedded source license/NOTICE separately; an upstream LICENSE alone cannot attest to the binary.
- Capture reviewer identity and timestamp, license text hashes for actual distributed versions, redistribution or hosted-only decision, proof of source/NOTICE availability, and every exception/waiver before marking accepted.
- No formal legal opinion or second-party independent review has been obtained; `REVIEW_REQUIRED` remains in effect.

# WEB-P0 third-party attribution inventory — DRAFT / REVIEW_REQUIRED

This file is a proposed source-attribution record for the **non-operational, unmerged WEB-P0 Next.js runtime**, not an approved distribution notice, license waiver or proof of compliance. It must be checked against the **actual exact-version tarball LICENSE/NOTICE text and shipped build artifact** by a qualified independent reviewer.

## caniuse-lite@1.0.30001820 — CC-BY-4.0

- **Package:** `pkg:npm/caniuse-lite@1.0.30001820` (transitive dependency of the pinned WEB-P0 runtime in `pnpm-lock.yaml`).
- **License declared:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
- **Source and attribution:** Can I Use browser compatibility data, https://caniuse.com/ — created and maintained by Alexis Deveria, with contributors. The reduced dataset is distributed through `browserslist/caniuse-lite` (author listed as Ben Briggs).
- **Upstream source:** https://github.com/browserslist/caniuse-lite
- **License terms:** https://creativecommons.org/licenses/by/4.0/legalcode
- **Attribution guidance from upstream:** https://github.com/Fyrd/caniuse — the upstream repository requests credit to caniuse.com.
- **Modifications by this repository:** No intentional modification of the upstream browser support dataset has been documented. **Whether the build transforms, bundles or redistributes portions of it has NOT been verified.** Do not describe third-party code or build output as unchanged without the review.
- **Distribution and notice obligation:** **REVIEW_REQUIRED**. Determine whether build-only use, server hosting, browser delivery, and any redistributed artifacts require additional credit, license copy, link, modification indication or accompanying third-party notice.
- **Status:** BLOCKED_PENDING_INDEPENDENT_LICENSE_REVIEW. In particular, this entry is **not** a `curated_assertion`, an addition to the P04 `allow` list, or an approved waiver.

## Acceptance and fail-closed boundary

1. A qualified independent security/license reviewer must verify the **exact pinned package** and actual package-license contents, and record the required attribution/distribution treatment in [WEB-P0 P04-F review issue #530](https://github.com/rahemih/Finance/issues/530).
2. The separate governed P04 policy decision must be explicit and scoped to exact-version evidence. Continue to **fail** `SBOM_LICENSE_MISSING` / review-class checks until all required authorizations and evidence exist.
3. Check user-visible credit and shipped notices **before** any future production or third-party distribution. No WEB-P0 deployment, real user login or trading is authorized by this document.
4. No A5/A8/A10, Syft, Trivy, P04 `allow/review/block`, protected-main or Human Gate protections are modified.

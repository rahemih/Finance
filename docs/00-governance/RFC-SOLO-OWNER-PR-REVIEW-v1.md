# RFC: Solo-Owner GitHub Pull-Request Governance for NEXUS QUANT

**Status:** POLICY_ADOPTED / PR_500_MERGED / POSTMERGE_GOVERNANCE_PASS; canonical reconciliation in FIN-P00-WX-001-R01  
**Task:** `FIN-P00-WX-001` — new governance addendum only; does **not** reopen closed canonical P00.
**Owner model:** one human repository owner, with assistant/automation as tools (never a separate GitHub reviewer).  
**Relevant WEB-P0 PRs:** [#496](https://github.com/rahemih/Finance/pull/496), [#497](https://github.com/rahemih/Finance/pull/497), [#498](https://github.com/rahemih/Finance/pull/498).

## 1. Verified GitHub policy, not an assumed future setting

At audit of 2026-10-31, repository ruleset `24412077` (**Protect main**) was active and targeted default branch `main`:

- `pull_request.required_approving_review_count = 0`; an extra collaborator and second GitHub identity are **not technically required** by the GitHub ruleset.
- Required status check: `governance`, `strict_required_status_checks_policy: true`.
- Linear history required; squash-only PR merges permitted; no branch deletion/non-fast-forward on protected `main`.
- This rule does **not** by itself waive any stricter project-specific security or Owner/Human Gate.
- Integration permission may block direct branch protection reads; Ruleset API is the evidenced policy source.

## 2. Proposed owner-attested solo route (non-live only)

**Only if Owner explicitly approves this RFC:** for documentation-only PRs and bounded, non-live implementation tasks *without a separate mandatory independent security review in their upstream contract*, the independent **GitHub human reviewer** slot may be `NOT_APPLICABLE (SOLO_OWNER)`, rather than fabricated `APPROVED`.

A0/assistant prepares:
1. Exact diff scope, Task Contract, frozen-roadmap consistency and dependencies.
2. Run-scoped CI evidence and specific outstanding test gaps, including security scans where relevant.
3. An Owner Decision Record with PR number, exact `head SHA`, relevant artifact digest, tests and risk, timestamp and identity, and stop/rollback plan.
4. GitHub comments and Linear update; Owner performs the actual Human Gate explicitly, **not** by asking GitHub to approve their own PR.
5. Merge stays blocked if any mandatory check, scope dependency, owner decision, required separate reviewer, or release acceptance gate is unresolved.
6. Once legitimately merged, postmerge `main` SHA + CI + docs/Linear reconcile; then and only then can task status become `CANONICAL_COMPLETE`.

The user may choose to invite an independent reviewer voluntarily. Nobody shall create a duplicate/impersonated account, self-review as an apparent external party, or fake independent approval.

## 3. Strict boundaries / cases where solo route does NOT replace independent scrutiny

- **A5 independent Risk veto** and P16 Pre-Trade Firewall, kill switch, order provenance, broker execution, OMS, risk ceilings, leverage and permissions remain separate enforceable domain controls. Owner/assistant may not override them by checkbox or AI response.
- Auth/Identity/WebAuthn, session, RBAC/CSRF, secrets, provider keys, security-critical runtime, deployment or sensitive workflow changes still require all explicit security tests and any mandated external/independent review. If a relevant frozen upstream contract requires independent human/security review, **BLOCK** until fulfilled or a specific owner-approved change process validly resolves it; this RFC does not silently waive it.
- `LIVE_TRADING` and `AUTO_TRADING` remain `DISABLED`. `P24-B` and `G13` remain unchanged. No LIVE acceptance or production readiness may follow from this policy.
- All 34 WEB-P0 pages and 212 reference images retain `REVIEW_REQUIRED` where applicable; no screenshot becomes a frozen owner baseline without explicit, image-specific approval. No unexecuted React/Next/Playwright/WCAG/API/E2E test is reported as PASS.
- Agent/static analysis results are independent **execution evidence**, not an independent human code reviewer. A0 cannot issue Owner authority.

## 4. Existing #496, #497 and #498 — do not infer consent or retroactivity

Those three PRs currently say **independent review + Owner Human Gate**. Their existing conditions remain in force until a signed Owner decision on this RFC **and** any PR-specific scope-change amendments.

**Suggested first application after Owner accepts this RFC:** PR #496 is a docs-only registration and may be explicitly designated `SOLO_OWNER_DOCS_ONLY` with required `governance` PASS and exact head+artifact Owner Gate. For #497 and #498, independently assess their higher-risk implementation requirements, P03 security scope, test limitations and separate review obligations; no automatic entitlement is granted by the #496 decision.

## 5. Proposed owner-approval text (NOT an approval)

> I approve FIN-P00-WX-001 solo-owner governance for non-live, non-sensitive documentation and appropriately bounded implementation PRs, while retaining all required status checks, exact-SHA Owner Human Gates, P03 security reviews, independent A5/P16 vetoes, visual baselines and Live/Auto blocks. I do not approve the merge of any particular PR solely by this policy decision.

Until a real, explicit Owner approval is recorded with the current task/PR version, **STATUS = PROPOSED / NO MERGE AUTHORITY**.

### Owner Policy Decision Record — 2026-10-31 (non-merge authorization)

The human Owner provided the exact affirmative statement in the Finance project ChatGPT conversation:

> قرارداد مدیریت تک‌نفره FIN-P00-WX-001 در PR #500 را با حفظ Human Gate، تست‌های اجباری و کنترل‌های مستقل امنیتی تأیید می‌کنم.

- Decision: **APPROVE SOLO-OWNER POLICY TEXT**, with all existing Human Gates, required tests and independent domain-security/risk controls retained. The owner did **not** authorize arbitrary PR merges, remove any independent review that an upstream sensitive workstream explicitly requires, or grant LIVE/AUTO permission.
- Decision source: the Owner's ChatGPT conversation message (not a GitHub review, not cryptographically signed, and not an independent second reviewer). GitHub PR and Linear contain a matching record. Do not present it as a GitHub APPROVED review.
- Approved policy revision when the Owner wrote the message: PR #500 head `ac045816500cebb1f082c629270d738732a90daf`; Governance Run `41186162019` **SUCCESS**; CI artifact `foundation-ci-manifest` SHA-256 `a079f57d20072e38690f33f27999653fe2ba527c8a48bfe9904c11a3ca076f7b`.
- This subsequent documentation-only amendment records the decision and does not expand the proposed policy. It requires **fresh CI on its new exact head** and an independent, explicit **PR-specific Owner merge Human Gate** before any merge.
- Effective/canonical status: **PENDING**. GitHub `main`, ruleset 24412077, #496/#497/#498 special gates, P24-B/G13 and LIVE/AUTO remain unchanged.

## 6. Rollback, audit, escalation

- Fail-closed: incomplete evidence, untrusted reviewer, external security review needed, or unapproved contract conflict = `BLOCKED` and no merge.
- Rollback proposed policy by closing draft PR; no repository ruleset/settings change required.
- After final acceptance, catalog/current-state/Linear evidence must cite the actual merged SHA; do not claim canonical policy merely from this draft.


## 7. Postmerge Owner Gate and canonical evidence — 2026-10-31

- Owner's separate PR #500 merge Human Gate explicitly named Head `ed71d8d3f503f6f0e16443ee80d7a6378de843f1` and Artifact SHA256 `405c4f319c7daf8c5d401225a893a1ce7a8514f634a05804c8dc0a32b48d555e`.
- Premerge `governance`: [41186435417](https://github.com/rahemih/Finance/actions/runs/41186435417) **SUCCESS**.
- GitHub API returned `merged=true` for [PR #500](https://github.com/rahemih/Finance/pull/500) and squash merge `a2371b10a2175889882f24931ff4be0dd3597e60`; `main` was independently read back at that exact SHA.
- Postmerge `main` Governance: [41186655318](https://github.com/rahemih/Finance/actions/runs/41186655318) **SUCCESS** and evidence artifact `foundation-ci-manifest` digest `sha256:a091f722bb5558d7c1b1ef576550b9796530978cb8dfd43bf2bd632dfe7ad013`.
- Postmerge Branch Hygiene: [41186655290](https://github.com/rahemih/Finance/actions/runs/41186655290) **SUCCESS**.
- Scope remains `SOLO_OWNER_NONLIVE` / `POLICY_ONLY`. Existing PRs #496, #497 and #498 remain separately gated and UNMERGED. A5 independent risk veto, P16 firewall, Auth security reviews, owner screenshot baselines, P24-B/G13 and `LIVE_TRADING/AUTO_TRADING=DISABLED` remain unchanged.
- This section reconciles historical PENDING status, not a new policy authorization. The repair itself is proposed in governed PR `FIN-P00-WX-001-R01` and is not canonical until that PR passes its own Owner gate, merge, and postmerge evidence.

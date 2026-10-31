# RFC — P24 synthetic-only owner-attested review exception for PRs #492, #493, #494, #499, #502

**Task:** `FIN-P24-WT-001`  
**Status:** `PROPOSED_NOT_EFFECTIVE / OWNER_POLICY_HUMAN_GATE_REQUIRED`  
**Source:** solo-owner policy `FIN-P00-WX-001` adopted in PR #500 and reconciled in PR #501.  
**This proposal is not approval to merge any candidate PR.**

## Problem and narrower solution

All five P24 support packages are bounded to synthetic/offline analytical work. Their original HIGH-risk Task Contracts require independent A5/A8/A10 reviews before merge. The repository has one human owner and no independent human PR reviewer. GitHub's `Protect main` ruleset requires the `governance` status check but **0 GitHub approvals**; repository settings alone cannot amend stricter Task Contracts.

The proposed solution is **not** to claim a second reviewer exists, nor to mark their review PASS. It is a *specific prospective owner-approved contract amendment*, limited to replacing the **independent second human GitHub code-review slot** on these five synthetic-only PRs. Each retains all automated and independently enforced domain safety checks, high-risk findings, evidence traceability and a separate **Owner SHA+artifact Human Gate** before merge.

This exception does **not** automatically apply on adoption. Each original PR must later amend its own Task Contract's review/DoD text to reference the newly merged exception, then pass fresh CI and obtain the owner PR-specific merge decision.

## Exact proposed scope

| PR | Task | What it does | Why only research |
| --- | --- | --- | --- |
| #492 | FIN-P24-WR-001 | FIBO/cTrader + Tabdeal reference contract | no SDK, external order or real account; owns transitional Current State/Task Catalog/Governance changes, requiring careful merge/lock closure |
| #493 | FIN-P24-WO-001 | synthetic stop, replay, A5 veto and audit-chain lab | **not** deployed Kill Switch; runtime halt cannot be waived |
| #494 | FIN-P24-WP-001 | sanitized unattested demo telemetry metrics | no broker attestation, account access or performance proof |
| #499 | FIN-P24-WQ-001 | mock Dukascopy/crypto independent-source comparison | synthetic only; real feed licensing/eligibility and TradingView restrictions unresolved |
| #502 | FIN-P24-WS-001 | local quote CSV import, quarantined source rights | no network, account/credential or source license certification |

Baseline branch heads and exact permissions are pinned in `config/governance/p24-offline-solo-review-proposal.json`. No retroactive approval: a changed HEAD, file scope or dependency triggers a fresh comparison and Owner decision.

## Non-negotiable controls and what 'independent' means

1. **A5 independent runtime Risk veto** and P16 Pre-Trade Firewall remain authoritative. A written review or owner decision must never override a veto.
2. **A8 security** negative checks, credential isolation, input provenance, no-network/order imports, dependency/SBOM and static analysis remain mandatory. Any actual security-sensitive or production auth/OMS/risk change invalidates this exception.
3. **A10 evidence** must independently verify the actual GitHub-run result, current HEAD, artifact digest, source-mode/provenance, negative tests and postmerge results. An A0 summary is not independent human attestation.
4. **Mandatory GitHub Governance, PR-specific CI and protected-branch rules** remain in force. Tests must not be waived, disabled or reported PASS before run completion.
5. **Separate explicit Owner Human Gate per PR** must contain the PR number, exact HEAD SHA, run IDs/artifact digest, accepted risk boundary and authorization to merge **that PR only**. A general 'continue' instruction cannot substitute for it.
6. A5/A8/A10 are distinct **control domains**, not invented extra human identities. Without independent humans, report `INDEPENDENT_HUMAN_REVIEW=NOT_APPLICABLE_OWNER_EXCEPTION` only after the specific exception is formally adopted. Never label `INDEPENDENT_HUMAN_APPROVED` or `G13=PASS`.
7. If a PR touches executable order routing, real broker connectivity, credentials, Auth/RBAC, production Kill Switch, increasing risk budgets, actual data entitlements, nonpublic account info, Live/Auto or frozen roadmap: **this exception fails closed; require separate applicable human/security gates**.

## Controlled application after Owner approves this exact RFC and it is merged

**Checkpoint A — policy:** Full `governance` + policy-test evidence at this RFC's latest head; owner approves this RFC's exact HEAD and artifact; squash merge, inspect main SHA, postmerge CI/Branch Hygiene and register in Linear. Until complete, policy remains `PROPOSED_NOT_EFFECTIVE`.

**Checkpoint B — five amendments:** One PR at a time, change only the eligible Task Contract review sentence / definition-of-done clause to:
> Independent second human GitHub review: NOT_APPLICABLE under merged FIN-P24-WT-001 for this exact synthetic-only scoped Task. A5 independent runtime veto, A8 security controls, A10 evidence and all mandatory CI stay REQUIRED. A separate Owner Human Gate per current PR HEAD+artifact is REQUIRED. This text is not a Live approval.

Re-run all applicable tests on the amended head. Record evidence, A5/A8/A10 negative-control matrix and reviewer eligibility. Stop on any scope or dependency drift.

**Checkpoint C — per-PR decision:** Owner explicitly grants or denies merge of the amended PR at exact current HEAD. If granted, squash merge sequentially with current-main verification and postmerge full Governance and Branch Hygiene. Do not merge all five based on one blanket gate.

**Checkpoint D — closure:** #492's provisional `LOCK ... ACQUIRED` in Current State and `IN_PROGRESS` in Task Catalog are **not** task completion. Use a separate governed closure PR after all source PR merges to release lock, update status, revalidate fresh main and reconcile Linear. Only then may bounded offline Tasks be `CANONICAL_COMPLETE`.

## Evidence and explicit non-claims

Verified before this proposal: five branch-head Governance PASS; 22+43+46+48+48 = **207/207 offline scoped tests**; no independent human reviews in those PRs. CI evidence does not prove the risk engine is production certified, data licensed or broker/demo performance real. New code and its artifacts are also subject to strict review.

**PRE_FIRST_LIVE=0/9**; `P24-B=BLOCKED`, `P24-C..I=NOT_STARTED`, `G13=NOT_STARTED`, `FIRST_LIVE_OWNER_GATE=NOT_GRANTED`, `LIVE_TRADING/AUTO_TRADING=DISABLED`. No account, real capital, trading credential or market-data rights are conferred.

## Proposed Owner decision (NOT YET GIVEN)

> قرارداد اصلاح محدود FIN-P24-WT-001 را فقط برای جایگزینی بازبین دوم GitHub در پنج PR آفلاین #492، #493، #494، #499 و #502 با مسیر Human Gate مستقل مالک، همراه با حفظ کامل کنترل‌های A5/A8/A10، تمام CIها، عدم مجوز Live و تأیید جداگانه هر PR پس از مشاهده Head و Artifact، تصویب می‌کنم. ادغام هیچ‌یک از این پنج PR با این تأیید کلی مجاز نیست.

The Owner must confirm the final policy revision and exact evidence before `FIN-P24-WT-001` itself can merge. Owner consent to 'solve the issue' authorizes preparing this proposal, not falsifying independent reviewer approvals or auto-merging branches.

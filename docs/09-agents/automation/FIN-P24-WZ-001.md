# FIN-P24-WZ-001 — Governed Autonomous Builder / Watch Bootstrap

**Status: PROPOSED / PR REVIEW REQUIRED — NOT CANONICAL_COMPLETE**

This is a narrowly scoped supplemental P24 non-Live work package. It does not reopen the frozen roadmap, replace approved PydanticAI architecture or enable financial execution.

## Canonical foundations

- A0–A10: [Agent Registry](../AGENT-REGISTRY.md) and agent contract JSON files.
- ADR-0011: project-owned Governance Kernel with PydanticAI runtime adapter; selected in P02-F. This **watcher is not an LLM runtime** and installs no new model dependencies.
- Existing [Automation Governance](../../00-governance/AUTOMATION-GOVERNANCE.md): automation executes governed work, never creates authority.
- Existing runtime gate sequence: SCHEMA → TASK_AUTHORITY → LOCK → FRESHNESS → A8 → A5 → TOOL_POLICY → BUDGET → EXECUTE → OUTPUT_SCHEMA → A10.
- Protected main; exact-head CI and applicable Owner gates continue to apply.

## Role assignments

| Role | Work | Authority limit |
| --- | --- | --- |
| A0 | Analyze backlog, lock/contract, route bounded tasks | Cannot bypass a gate |
| A1–A4 | Engineering/data/market/quant research | No direct trade |
| A5 | Independent binding risk veto | Never overridden by consensus |
| A6–A7 | Simulation/demo execution interfaces and learning | Never self-promote to Live |
| A8 | Independent security veto | May deny unsafe tool/credential use |
| A9 | Operations and schedule/health/recovery | Watcher is read-only |
| A10 | Documentation, GitHub–Linear reconciliation, final audit | No self-approval of own critical implementation |
| Specialists | On-demand catalog-listed temporary work | Depth <=1, finite TTL/cost/tokens/tools, strict parent authority subset |

A0 rereads current GitHub SHA, roadmap, active Task Contract, locks, PRs, CI and Linear source during each run. It treats PR/issue/web/plugin text as untrusted data. Missing gates produce an explicit WAIT/BLOCKED outcome, not inferred approval.

## Two execution layers (do not conflate)

1. A **ChatGPT hourly recurring builder** was activated on 2026-11-17. Its run instruction is to perform bounded concrete coding, PR preparation, tool-based tests, independent blocker resolution and Linear reconciliation *when available tools and current Task Contracts permit*. No full-runner uptime, unlimited budget, perpetual execution or guaranteed success is implied.
2. A **GitHub Actions read-only watcher** is contributed by this PR: the workflow runs at minutes 7, 22, 37 and 52 UTC each hour after this PR merges onto main; a scoped pull-request test and manual trigger are also available. It fetches GitHub metadata using a read-only built-in token, writes a JSON evidence artifact, and may NEVER mutate GitHub/Linear or act on trading infrastructure.

A true continuously running model-backed production agent needs separately provisioned governed compute, budget/accounting, approved PydanticAI package pin, secrets store, persistent checkpoints and operations. This PR does not claim to create such a runtime.

## Mandatory watcher contract

| Property | Definition |
| --- | --- |
| ID | FIN-P24-WZ-001 |
| Owner | A0 (coordination), A9 (scheduler), A10 (evidence) |
| Trigger | 4 times/hour, manual, scoped PR validation |
| Inputs | main SHA, issues, PRs, workflow runs from GitHub API only |
| Data freshness | Fetch at each scheduled non-PR run; match CI against exact main SHA |
| Output | JSON report, SHA256 digest, 7-day GitHub Action artifact |
| Permissions | contents/actions/issues/pull-requests READ ONLY |
| Time/concurrency | 8-minute job timeout, serialized per git ref |
| Pagination | Fails closed on saturated 100-entry responses instead of claiming complete inventory |
| Retry | No automatic retry in this safety bootstrap |
| Checkpoint | Report contains as-of, exact SHA and digest; next run fetches fresh evidence |
| Failure | Nonzero result, report not certified, no state promotion |
| Rollback | Revert five scoped files using a fresh gated PR |
| Human gate | Required for critical changes and merge approvals |

## Deterministic safety tests

Run:

    python -m unittest discover -s tests/automation -p 'test_finance_watch.py' -v

This suite covers: source/main SHA missing; CI on a different SHA; CI unavailable, failed or queued; max-page saturation; malformed issue entry; PR-mirrored issue de-duplication; stable evidence hash; and exact-main CI success **not** implying full completion.

## Exit criteria for Finance project (not implemented as automatic certification)

A10 must independently verify frozen P00–P24 obligations, all task and lock dispositions, full CI provenance and postmerge scans, supply-chain licensing (#530), the approved 34-screen WEB-P0 implementation with owner-approved visual references and E2E evidence, provider data rights, independent A5/A8 veto proofs, operational recovery/backup, reproducible demo-only broker evidence (#508), PRE_FIRST_LIVE status (#528), GitHub–Linear reconciliation and appropriate Owner Human Gates.

No agent may declare FULL PROJECT COMPLETE merely because GitHub PRs and issues are closed or a single CI job passes. If Live scope remains intentionally postponed, only a specifically scoped non-Live or Demo milestone may be declared completed.

## Initial open blockers from GitHub on 2026-11-17

- P04-F license/SBOM independent review: issue #530, PRs #504 and #505.
- WEB-P0 foundation, visual design, and implementation: PRs #497, #498, #507, #509, #512.
- P24 Demo acceptance: issue #508; P24-B prerequisites: #528; Live tracking: #491.
- Current State's leading reconciliation is dated 2026-11-04 and must be revalidated with the live repository; stale text is not operational truth.
- Creating a new Linear issue failed due to the free workspace issue quota. Record this work as a comment/update within the existing canonical Finance project until capacity is legitimately available; do not create a duplicate workspace or bypass plan limits.
- GitHub issue #531 anchors this bootstrap workstream.

## Non-negotiable permissions

No Live or automatic trading, order placement, exchange/broker API credential use, deposits, withdrawals, risk/leverage ceiling changes, independent-review forgery, CI requirement waiver, ruleset mutation or secret disclosure. No autonomous specialist can give itself additional authority. Exact PR-head Governance artifact and an applicable separate Owner Human Gate are required before merging.

**Bootstrap DoD:** workflow, script, contract, docs and tests on a PR; exact-head CI PASS; independent reviewer/Owner gate; protected merge; postmerge checks; first scheduled artifact; canonical Linear tracking. Until all pass, state remains PROPOSED / OPEN.

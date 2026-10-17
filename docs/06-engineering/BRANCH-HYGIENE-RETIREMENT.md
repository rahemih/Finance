# Branch Hygiene Retirement — FIN-P04-WF-001-R01

State: CANONICAL_COMPLETE after governed merge

## Purpose

Resolve automated branch-hygiene issue #233 without weakening the threshold or deleting unproven work.

## Safe absorption rule

A branch with no open PR may be deleted when its **current tip commit** is associated by GitHub with a merged same-repository pull request. The branch name does not need to equal the historical PR head name because several historical aliases point at commits already absorbed through another governed branch.

The following current branch tips have merged-PR association evidence:

| Branch | Tip / proof |
|---|---|
| `agents/FIN-P01-WG-002-build-readiness` | tip commit associated with merged PR #43 |
| `architecture/FIN-P02-WA-001-principles-adr-framework` | tip commit associated with merged PR #58 |
| `docs/FIN-P18-WI-001-phase-close` | tip commit associated with merged PR #381 |
| `docs/P18-continuous-demo-learning-phase-closure` | same absorbed P18 closure tip / merged PR #381 |
| `research/FIN-P01-WD-001-compliance-jurisdiction-R02` | tip commit associated with merged PR #34 |
| `risk/FIN-P15-WA-001-risk-policy-budget-hierarchy` | tip commit associated with merged PR #302 |

## Explicit superseded proof set

Three additional branches are eligible only after the workflow verifies the exact closed PR, exact head branch and exact head SHA at runtime:

| Branch | Closed PR | Superseded by |
|---|---:|---|
| `feat/FIN-P18-WE-001-controlled-retraining` | #375 | canonical P18-E PRs #369/#370 |
| `docs/FIN-P15-WB-001-position-sizing-close` | #313 | canonical P15-B closure PR #306 |
| `docs/FIN-P00-WY-001-canonical-close` | #247 | canonical staged-scaling closure PR #246 |

No generic stale/unique branch is added to this exception set.

## Guardrails

- main/default branch is never deleted;
- branches with open PRs are always kept;
- protected branches are kept unless canonical safeguards allow them;
- unprotected branches with `ahead_by=0` remain safely deletable;
- an ahead branch without merged-commit proof or exact superseded proof remains report-only;
- the configured warning threshold remains 12; it is not raised to hide branch debt.

## Audit

The audit job now also runs after main pushes following cleanup. Therefore a cleanup that really brings inventory within policy closes #233 automatically; otherwise the workflow fails and keeps/updates the issue.

P19 remains NOT_STARTED. This repair has no trading/runtime authority.

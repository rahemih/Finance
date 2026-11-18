# FIN-P24-WZ-005 — Governed Autonomous Code-Fix Runner

**Current state: ENGINEERING PROPOSAL / PR REVIEW — NOT RUNNING AS AN AUTONOMOUS CODER.**

This package turns the fixed Mission Control audit roadmap into a real *candidate* code-writing engine. The workflow uses GitHub Copilot CLI to edit a temporary checkout, run baseline foundation tests and construct an **untested** verifiable patch and open a **draft-only** PR in an independently privileged job. It never routes orders, alters Live/Auto trading permissions, or impersonates A5/A8/A10 independent reviewers.

## Source of truth and task selection

- Repo: rahemih/Finance; reference: protected main SHA. No stale chat memory/Issue wording authorizes code changes.
- Current fixed task: docs/09-agents/automation/tasks/FIN-P24-WZ-005.json (doctor reliability regression tests).
- Allowed candidate file paths are exactly scripts/dev/doctor.py and tests/foundation/test_dev_doctor.py.
- Run the foundation unit suite, propose a small code/test fix, run suite again, and retry model-assisted correction **at most two attempts**.
- Do not run on pull_request with secrets; only scheduled and workflow_dispatch on protected main. Automatically skip if an open FIN-P24-WZ-005 PR exists.

## Model/runtime

- GitHub Copilot CLI is an ephemeral **Actions-only** tool; pinned @github/copilot@1.0.112. No version upgrades or production dependencies without governance.
- Agent job gets **contents: read**; no GitHub write token. Copilot CLI noninteractive permissions: edit/view/grep/glob, read+write local checkout, deny shell and URL; all patch contents are rejected if they stray from the exact Task Contract.
- Missing or invalid COPILOT_GITHUB_TOKEN is a terminal **BLOCKED** run with a report, not a fake success. A ChatGPT Plus subscription does not automatically supply a Copilot API entitlement.
- GitHub Models (old inference API) was retired July 30, 2026. Never rely on deprecated endpoint.
- Copilot agent is restricted to one bounded task. A0/A1/A8/A9/A10 telemetry is **a role-labelled execution record**, not proof of physically independent model agents.

## One-time private GitHub setup before real code generation

1. In GitHub, verify that the account/repository is eligible for GitHub Copilot CLI programmatic requests.
2. Create a user-owned, limited fine-grained token with **Copilot Requests: read** permission (not full repository admin). Store it only as Actions repository secret COPILOT_GITHUB_TOKEN under Settings > Secrets and variables > Actions.
3. Optional: to see A1/A9 steps immediately in the passwordless public Mission Control, add Actions secret NQ_TRACE_TOKEN with the same private token as Render's NQ_INGEST_TOKEN. Keep telemetry free of PII and credentials. Without this optional secret GitHub Actions logs/runs remain observable via the dashboard's GitHub feed.
4. Review the workflow, tests and required owner/independent PR gates, then merge it through protected main. **This PR itself does not bypass that approval.**

A secret value must never be pasted into PRs, documentation, public dashboard, Issues or chats.

## GitHub Actions workflow

- Path: .github/workflows/finance-autonomous-coder.yml
- Triggers: schedule UTC 43 */6 * * *; owner manual workflow_dispatch.
- Runs only from main; serialized concurrency, bounded 24-minute build job + 10-minute publisher.
- Preflight: inspect open PRs, avoid duplicate tasks, fail if incomplete pagination.
- Model phase: run trusted baseline tests before any edits, invoke pinned Copilot CLI up to two times, forbid shell/network tools, validate changed paths, generate <=32KiB patch and SHA256 evidence. **Never execute AI-modified Python in this token-bearing job.**
- Validation: a separate **credential-free, read-only Actions job** checks the untrusted patch before applying, executes the Python foundation suite with no Copilot secret and marks tests as verified only after an actual pass.\n- Publisher: a third separate job with temporary Actions token; **never executes AI-authored code**, revalidates exact main SHA, hashes, altered paths, size, tested evidence and scope, creates a draft-only PR, dispatches Governance Verify on that PR branch.
- A PR created using GITHUB_TOKEN may not trigger pull_request CI. The dispatch is explicit, but full exact-PR-head and independent gate evidence must still be verified. Never declare canonical complete based merely on that dispatch.
- A separate non-AI PR test workflow finance-coder-contract.yml validates code contracts with no inference credentials.

## Evidence / output

- GitHub Actions logs, task ID, main SHA, model iteration count, separate credential-free test job, tests status, patch SHA256, changed-file list, run summary in build/finance-coder/report.json and seven-day validated artifact.
- Optional bounded Runner -> Mission Control /api/events POST with private NQ_TRACE_TOKEN; SSE forwards authenticated-source events without certifying separate A5/A8/A10 identities.
- Full errors, raw model response and secret-bearing contents are deliberately **not** copied into public events.

## Reliability, security and expansion

- Fatal missing entitlement, unrecognized model, permission/API rate limit, or unsafe change => BLOCKED, not "fixed".
- Runtime failures and test failures have a **finite** retry budget. Repeated runs detect an open task PR and stop instead of duplicating changes.
- No automatic merge or CI gate bypass; independent A5/A8/A10 and owner review stay mandatory. Failed independent validation is terminal for that run; automatic model retry after a failing isolated test is deliberately disabled until a durable, budgeted remediation loop is reviewed.
- Additional coding tasks must be added one-by-one through an explicit allowlisted, reviewed Task Contract. **A single task cannot complete the entire P00–P24 roadmap.**
- Preview Render Free is not a 24/7 persistent engine; all code generation runs on GitHub Actions after workflows are merged and provider credentials have been separately provisioned.
- Budget: up to four scheduled attempts per day, 2 model calls each, model and Actions quotas external. No paid subscription or unlimited budget is silently authorized.
- Failure state requires a checkpoint on GitHub and task/Issue/Linear reconciliation before starting another independent work package.

## Exit criteria

Run real Copilot inference successfully, produce a scoped patch and actual *draft PR* through the privileged publisher, observe exact-head tests and independent reviews, reconcile GitHub + Linear, record postmerge evidence if authorized, then close **FIN-P24-WZ-005 only**. Finance remains incomplete until all frozen scope and production/demo/legal/provider requirements have independent evidence.

### Sources for 2026 provider setup

- GitHub Docs: https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-in-actions
- GitHub Docs: https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically
- GitHub Docs: https://github.github.com/gh-aw/reference/safe-outputs/

## 2026-11-18 security correction: isolation of untrusted tests

Generated code is untrusted. The initial model+test design risked running newly edited Python while `COPILOT_GITHUB_TOKEN` existed in the process environment. The corrected workflow intentionally produces `CANDIDATE_UNTESTED` in the model job; a separate read-only `validate` job (no inference token) checks patch integrity and runs the tests, then writes a `READY_FOR_PR_REVIEW` artifact. The independent publisher accepts only that verified artifact. An isolated test failure never returns an apparent success or triggers an unbounded model loop. Actual production acceptance awaits successful exact-head workflow checks and genuine Copilot inference evidence.

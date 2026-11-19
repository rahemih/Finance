# P24 independent review evidence — fail-closed checkpoint

Status: **DRAFT / NO INDEPENDENT APPROVAL**. This document is an evidence template, not a governance exception or a review submission.

## Identity and independence

A5 (Risk), A8 (Security) and A10 (Evidence/Governance) are **defined project roles**. A role name, generated agent trace, ChatGPT-authored report, or three different prompts do not establish three independent reviewers. Do not record `APPROVED` without a verifiable independent reviewer identity, scope, timestamp, exact PR HEAD and actual GitHub review/approved contract evidence. A single actor cannot independently approve its own implementation. Owner Human Gate is separate from these vetoes.

## Exact-head review checklist

| Role | Minimum evidence | Result |
| --- | --- | --- |
| A5 | Demo-only boundary, no Live/Auto or broker/orders/funds, risk veto and rollback | NOT_REVIEWED |
| A8 | Untrusted inputs, forged origin, HTTPS fail-closed, authentication, SSRF, secret exposure and negative tests | NOT_REVIEWED |
| A10 | SHA and CI provenance, mandatory checks, dependencies/stack, task contracts, lock and Linear parity | NOT_REVIEWED |

For each review record: reviewer GitHub identity/team; demonstrated independence from author and other reviewers; role; PR number; exact 40-character HEAD; reviewed diff and dependency SHAs; test run IDs; findings; verdict (APPROVE / REQUEST_CHANGES / BLOCKED); timestamp; link to immutable evidence. Unknown values mean BLOCKED, not PASS.

## Current scoped example — PR #536 (2026-11-19)

- HEAD: `aea84dc5c89495fb0219c7a00ebebb339f36d92c`; stacked on #535 and #533.
- Owner exact-head Human Gate: recorded, **conditional**.
- Mission Control API Verification run 44533703881 and Governance Verify run 44533703693: success for that head at last inspection.
- Independent GitHub review submissions at last inspection: **zero**.
- Do **not** merge #536 until independent A5/A8/A10 approvals, required checks, protected merge policy, exact-head locks and stack dependencies are verified. Any HEAD change invalidates the old exact-head Owner Gate.
- No paid model API, Copilot CLI, Live/Auto trading or financial transfer is authorized.

This document does not change existing policy. If independent reviewers cannot be provisioned, report the blocker and continue unrelated safe work; never fabricate reviewer approval or bypass branch protection.

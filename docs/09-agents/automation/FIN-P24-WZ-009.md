# FIN-P24-WZ-009 — Owner-authenticated Mission Control Start

**Scope: owner action to dispatch a fixed code task, not an anonymous public code execution API.**

## Architecture

The passwordless dashboard remains freely viewable, but mutating/billable operations are protected. A new "شروع کدنویسی واقعی" control is distinct from the existing read-only Start audit. GET /api/launcher reports only whether configuration is present. POST /api/launch accepts exactly `{"action":"run_fixed_governed_task"}`, verifies the owner authorization Bearer token with constant-time comparison, exact same-origin and Sec-Fetch-Site, a 30-minute per-instance rate cap, then dispatches only `finance-openai-builder.yml` on protected `main`. The request cannot select a different task, repository, workflow, branch, model, spending budget, or code path.

The server reports `DISPATCH_ACCEPTED` **only** after GitHub returns 204. This **does not** prove that inference or testing completed. Future GitHub Actions run/steps/PR are the independent operational proof.

## Private configuration prerequisites

- Render `NQ_OWNER_START_TOKEN`: a long unique random owner-only secret, >=32 bytes. The browser does not save it in LocalStorage, cookies or the repo. It is supplied on each privileged request and cleared from the input after submission.
- Render `NQ_GITHUB_DISPATCH_TOKEN`: separately scoped fine-grained Github token for `rahemih/Finance`, Actions workflows: write only where possible. Never send this token to the browser.
- Render `NQ_PUBLIC_ORIGIN=https://nq-agent-mission-preview-zeqg.onrender.com`, exact HTTPS origin already used by the preview.
- GitHub Actions `OPENAI_API_KEY`: distinct project-scoped OpenAI Platform API key; never in Render or the public browser. Account billing/limits must be owner approved.
- `finance-openai-builder.yml` must first be independently reviewed and merged into protected `main` so GitHub supports workflow_dispatch.

Without these prerequisites, the owner coding control visibly shows `BLOCKED_CONFIGURATION`, while public audit and historical CI remain viewable. A configured dispatch with a missing workflow yields `BLOCKED_GITHUB_DISPATCH`. **No bypass, no false active agent animation**.

## Operational tests

- `python -m unittest discover -s tests/automation -p test_mission_launcher.py -v`
- PR-head `P24 Mission Control API Verification` and `Governance Verify`.
- Test GET /api/launcher in deployed preview; must never expose tokens.
- Authenticated POST /api/launch must show GitHub 204 only after main workflow exists; 401/403/422/429/502 cases must not create spending jobs.
- Inspect exact Github Actions execution, real OpenAI response, credential-free test job and Draft PR with independent approvals. None of these can be inferred from 202 dispatch alone.

## Limits

Render Free can sleep and lose in-memory cooldown/journal on restart. Production owner controls require a durable rate limiter and job ledger, stronger OAuth/SSO identity and paid always-on infrastructure. This preview deliberately cannot honestly claim guaranteed 24/7 operation. The existing ChatGPT automation is independent of the OpenAI API-backed runner; the dashboard does not remotely start this ChatGPT conversation. Live/Auto trading remains disabled.

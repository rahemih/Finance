# FIN-P24-WZ-008 — Direct OpenAI Governed Coding Runner

**Implementation state: PR candidate; does not certify autonomous completion.** No GitHub Copilot is used.

## Intent

Owner wants direct OpenAI model engineering, not GitHub Copilot CLI. The ChatGPT conversation itself and scheduled ChatGPT automation are different runtimes from a hosted OpenAI API application. This GitHub Actions worker uses the **OpenAI Responses API** under an independently provisioned and billed API key. Do not portray it as this live ChatGPT conversation or an unconstrained always-on multi-agent cluster.

The fixed first task hardens the developer tooling helper so exceptions never reveal sensitive command arguments. It can only edit `scripts/dev/common.py` and add/modify `tests/foundation/test_dev_common.py` under a schema-validated manifest. No editing arbitrary PRs, credentials, financial tools or CI.

## Control loop and least-privilege separation

1. **Preflight (GitHub read-only):** check an exact open-PR task marker, fail if GitHub evidence is unavailable, skip duplicates. Main only.
2. **Propose (OpenAI credential):** send the two small source files and the fixed task to Responses API `https://api.openai.com/v1/responses` using a private Actions `OPENAI_API_KEY`. Model has **no shell, tools or GitHub write token** and returns a constrained JSON replacement proposal. Two retries maximum for malformed/incomplete proposals. Output is marked `CANDIDATE_UNTESTED`; NO generated code is executed in this job.
3. **Validate (no OpenAI key, no GitHub write permission):** fetch exact-run candidate, recheck SHA256/base/allowlist, materialize only the allowed Python files and execute the real `tests/foundation` suite. Only an actual green exit code permits a verified artifact.
4. **Publish (no OpenAI key; short-lived GitHub repo token):** check that original main SHA is still current, prevent duplicate PRs, revalidate proposal/verified artifact independently, create an isolated branch and a **draft-only** PR, request a real Governance run. Publisher NEVER executes model-generated Python.
5. **Independent review:** exact-HEAD CI, separate A5/A8/A10 and owner review must occur before protected merge. No merged status is inferred from CI green.

The Actions workflow is scheduled daily at 03:26 UTC after it is *approved and merged into protected main*; it also supports a GitHub-authenticated manual `workflow_dispatch`. Schedule is not continuous execution, and GitHub Actions and API budgets may apply. Free Render is not a persistent coding runner.

## Credentials / blocking dependencies

- `OPENAI_API_KEY` is not the previous `COPILOT_GITHUB_TOKEN` and is **not** included with the ChatGPT Plus subscription. It must be created by the owner via OpenAI Platform setup and placed privately in GitHub Finance → Settings → Secrets and variables → Actions. Never paste it into chat, commits, PRs or dashboard. Its use may be billable; set strict spend limits and restricted project permissions.
- Optional `NQ_OPENAI_MODEL` repository variable selects the model if the default is not enabled for the account. It is not a secret.
- GitHub Actions policy must permit draft PR creation from `GITHUB_TOKEN`. This is subject to existing organization/repo controls, not an authorization to weaken branch protection.
- GitHub `workflow_dispatch` requires the workflow to exist on the default branch, so attempts to dispatch it while this is a draft PR are not a valid live acceptance test.
- Render preview's passwordless public Start button remains **read-only** until a separately authenticated operator control plane is provided. Exposing a billable mutation operation to any anonymous visitor is unacceptable.

## Evidence and testing

Offline CI command:

    python -m unittest discover -s tests/automation -p 'test_openai_coder.py' -v

Run workflow contract tests; all must pass at exact PR head. Negative tests include invalid Python, path traversal, unauthenticated API fail-closed, integrity/SHA mismatch, invalid Live mode, limit of two model retries, mock successful code candidate and requirement for independent verified artifact. Mock tests never claim real inference.

Real acceptance once safe prerequisites are satisfied: observed OpenAI response, generation artifact hash, green credential-free test job, guarded draft PR, separate CI and independent reviews, and GitHub-Linear reconciliation. Do not mark task complete merely because mocks or contract tests pass.

## Dashboard telemetry

The current Mission Control SSE forwards authentic GitHub Actions results already fetched server-side, but does not receive private model steps unless a separate token-protected event adapter is provisioned. The dashboard must distinguish:

- `IDLE`: no authenticated run pending.
- `BLOCKED`: OpenAI API key missing, account unavailable, unsupported model or required review not done.
- `CODING`: actual OpenAI Responses API call observed.
- `TESTING`: actual credential-free CI step executing.
- `PROPOSED`: guarded draft PR created; NOT fully merged.
- `PROJECT_COMPLETE`: never inferred from a single task.

## Unresolved full-project dependencies

Full autonomous completion of P00–P24 also requires a protected task queue, durable checkpoints, independent A5/A8/A10 veto workers, real GitHub–Linear bidirectional sync, WEB-P0 UX/E2E, licence/SBOM review, broker/demo proof, secrets lifecycle, sufficient compute and a persistent queue. None can be bypassed by activating a model key. Live trading remains disabled.

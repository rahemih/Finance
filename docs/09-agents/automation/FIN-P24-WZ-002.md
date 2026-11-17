# FIN-P24-WZ-002 — Agent Mission Control trace instrumentation

Status: PROPOSED / DRAFT PR. **Not a functioning independent A0–A10 runtime.** Workstream linked to finance dashboard observability request; frozen P00–P24 scope unchanged.

## Purpose

Provide a safe event-protocol and standalone Persian RTL observability viewer, which can distinguish trusted current GitHub Actions data from *imported, self-reported* local agent traces. **No false activity**: the core roles defined by Agent Registry are not treated as running merely because a user can view their cards.

## Boundaries

- Demo/Simulation-only. Live trading, accounts, withdrawals, asset transfer, broker/exchange connectors, trading operations, external writes, and credential capture are all out of scope.
- ADR-0011 remains authoritative: project-owned Governance Kernel + PydanticAI adapter. This task adds observability primitives, not a runtime or authority system.
- Keep A5 independent Risk veto, A8 Security veto and A10 audit. An `AGENT_FINISHED` event does not certify any gate, test or completion.
- The event producer must already hold an active Task Contract and appropriate permission to act; emitting an event grants **zero authority**.
- Specialists cannot spawn recursively or expand authority. This journal cannot replace real governance checks.
- Owner authorizes autonomous non-live development and tests, but governance requirements for exact-head protected merge or independent review remain tracked in the repository. Any removal/alteration requires a separate scoped governed proposal.

## Files

- `scripts/automation/agent_trace.py`: Python 3 stdlib journal with cross-process lock, append and hash-chain verification, fixed event types, a minimal sanitized field set, no network or external actions.
- `tests/automation/test_agent_trace.py`: tampering, deletion, out-of-order, sensitive payload/paths, unknown agents/events and financial-mode rejection tests.
- `apps/agent-mission-control/index.html`, `app.js`, `trace-ui.js`, `styles.css`: responsive dark RTL dashboard. GitHub public read-only API data auto-refreshes in normal browser; trace import uses only a user-selected JSON report file, validated via browser crypto before rendering. No login, proxy, public telemetry endpoint, direct order surface or hidden credential collection.
- `tests/automation/test_trace_browser.js`: runs browser trace integrity checks with built-in Node crypto/vm.
- `.github/workflows/p24-agent-telemetry.yml`: scoped CI tests with minimum read-only permissions.

## Example local operation (explicit human/test-runner emission)

```bash
python scripts/automation/agent_trace.py emit --journal build/agent-trace/events.jsonl --agent A1 --task FIN-P24-WZ-002 --run demo-test-1 --type TEST_STARTED --message "Synthetic validation test only" --target tests/automation/test_agent_trace.py
python scripts/automation/agent_trace.py export --journal build/agent-trace/events.jsonl --output build/agent-trace/events.json
```

Open the dashboard's `index.html` from the same directory as `app.js`, `trace-ui.js` and `styles.css`, then import `events.json`. A local export is **not** live streaming, and its hash chain alone does not authenticate sender identity; consumers must not treat it as authoritative execution proof. Real agents need independently authenticated event transport, provenance, ingestion, retention and live delivery before showing truly current agent activity. The viewer always distinguishes imported traces from authoritative GitHub data.

## Security model

- No automatic collection of raw shell output, source code, environment variables or API credentials.
- Exact allowlist of event types and A0–A10 role labels. Paths cannot be absolute/traversal/sensitive.
- Digest chain provides local accidental/tamper detection only. A local attacker could rewrite the entire file; no digital signature or remote immutability is claimed.
- Invalid/missing/reordered/tampered events are rejected. Event count and file size are bounded.
- UI escapes all imported strings; it does not evaluate or execute imported code. No query parameters for secrets.
- Viewer never sends event data to GitHub; only GitHub public GET requests for CI/PR/Issue data.
- Static public hosting is safe only for *public metadata*. Do not upload private traces or account identifiers.

## Verification plan and lifecycle

1. Create PR with scoped contract, script, tests, HTML/CSS/JS and workflow.
2. Run Python negative tests, Node browser integrity checks and syntax checks locally.
3. Confirm exact-head scoped CI and full Governance in GitHub; identify any required independent review and owner-specific merge gates without forged approvals.
4. After permitted merge, verify main SHA, mandatory postmerge CI and deployment/hosting separately.
5. Integrate real Runner event emitters later under a new, explicit Task Contract and authenticated transport design; only then describe the UI as **live agent stream**.

## Known limitations

- No server/service is deployed; no agent's internal reasoning/typing can be observed without instrumentation in that runner.
- Public GitHub GET polling can be rate-limited or blocked from local file pages. Fallback snapshot is explicitly dated and not "live".
- Uploading an offline trace is not proof that the claimed agent was running. Neither hash chain nor an agent label certifies an independent risk/security review.
- No automatic final-project-completion assertion; that requires a full A10 evidence audit and all relevant project gates.

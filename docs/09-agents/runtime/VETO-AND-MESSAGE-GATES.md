# Deterministic Veto & Message Gates

## Gate order

`SCHEMA → TASK_AUTHORITY → LOCK → FRESHNESS → SECURITY(A8) → RISK(A5) → TOOL_POLICY → BUDGET → EXECUTE → OUTPUT_SCHEMA → A10_EVIDENCE`

No downstream PASS can override an upstream FAIL.

## A8 security veto

Binding outcomes: `PASS | DENY | WAIT_SECURITY_REVIEW`.

DENY conditions include prompt injection/tool-abuse attempt, untrusted instruction crossing trust boundary, secret exposure, permission expansion, disallowed tool, invalid provenance, unsafe dependency/runtime action or corrupted checkpoint.

## A5 risk veto

Binding outcomes: `PASS | NO_TRADE | WAIT_RISK_REVIEW`.

A5 is mandatory for any future execution-capable decision path. Missing/stale risk inputs fail closed.

## Message-envelope validation

Before any handoff or output is accepted, require:
- registered sender/receiver authority;
- valid schema version;
- task_id/run_id correlation;
- source refs and timestamps;
- assumptions/supporting/opposing evidence/conflicts;
- confidence/uncertainty/risk flags;
- action_class;
- limitations;
- tool_trace_id where tools ran.

Malformed, unknown-version or provenance-deficient envelopes are rejected and never auto-coerced into executable actions.

# State, Checkpoint & Resume Freshness Specification

## Canonical state principles

Checkpoint data is operational continuity, not authority. Task Contracts, canonical repository state and governed datasets remain external sources of truth.

## Checkpoint payload

Required fields:
- schema_version;
- task_id/run_id/agent_id/specialist_id;
- contract hash/version;
- model id/version;
- completed step ids;
- pending handoffs;
- source refs with source_as_of and retrieved_at;
- freshness policy snapshot;
- A5/A8 decision refs;
- tool trace refs;
- retry counters;
- budgets consumed/remaining;
- circuit-breaker state;
- last immutable evidence id.

## Resume sequence

1. Load checkpoint.
2. Verify schema and integrity.
3. Re-read current Task Contract and compare hash/version.
4. Revalidate locks and authority.
5. Revalidate A5/A8 decisions if their validity window expired.
6. Recheck critical source freshness.
7. Reconcile pending tool side effects/idempotency.
8. Resume only if all mandatory checks pass.

Any mismatch that can affect authority, financial risk, security, provenance or data freshness forces `WAIT`, `NO_TRADE` or `INSUFFICIENT_EVIDENCE`.

## Memory

Conversation/agent memory may help recall context but cannot satisfy evidence, authorization, risk or security requirements.

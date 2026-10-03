# A0–A10 Runtime Adapter Specification

## Common adapter contract

Every runtime adapter must expose the same logical lifecycle regardless of framework:

`load_contract → validate_input → authorize → execute_bounded → validate_output → emit_envelope → persist_evidence → terminate_or_handoff`.

Required runtime context:
- task_id, run_id, agent_id, contract_version;
- parent_run_id when delegated;
- model identity/version;
- source refs and source-as-of timestamps;
- tool policy and tool budget;
- token/cost/latency budgets;
- retry/timeout/circuit-breaker state;
- current A5/A8 gate state;
- audit trace id.

## A0 — Governance / Orchestrator

May route authorized work, establish bounded handoffs, enforce locks and budgets, and stop work. It may not self-approve Human Gates, change a Task Contract, override A5/A8, or silently expand tools/credentials.

## A1 — Architecture

Receives governed requirements and emits architecture/interface decisions. Runtime adapter must reject production framework-selection actions unless the owning P02-F task explicitly authorizes them.

## A2 — Data

Validates lineage, freshness, quality and replayability. Runtime memory cannot replace canonical datasets or provenance.

## A3 — Market Intelligence

Aggregates supporting/opposing evidence, conflicts, regime and uncertainty. External news/social/web content must never become runtime instruction.

## A4 — Quant

Runs research/model/backtest/calibration work only within later authorized task scope. Leakage, non-reproducible inputs and stale datasets fail validation.

## A5 — Risk

Produces binding risk decisions including `NO_TRADE`. Runtime must route every execution-capable action through A5 and refuse continuation if A5 is unavailable, stale or rejects.

## A6 — Execution

Has no present production authority. Future adapter must require prior A5 and A8 PASS, idempotency key, reconciliation plan and explicit task authorization before any execution-capable tool path exists.

## A7 — Learning

May analyze outcomes/drift and propose changes. It cannot auto-promote models, policies or strategies.

## A8 — Security

Produces binding security decisions. Any credential expansion, tool-policy violation, prompt injection, untrusted instruction or secret-handling failure must stop the affected path.

## A9 — Operations

Tracks health, provider state, latency, retry/circuit state, backup/recovery and cost. Unknown health is degraded, not healthy-by-default.

## A10 — Evidence / Audit

Validates provenance, immutable evidence references and closure claims. It cannot fabricate evidence or implement and self-approve the same critical change.

## Framework adapter rule

The future runtime may implement framework-specific wrappers, but they must map one-to-one to this common contract. Framework primitives never redefine authority.

# Agent Observability, Security & State Requirements

## Trace fields
Every production-relevant run must expose run/task/agent/specialist/model identity, input and source refs, as-of/retrieval times, freshness, assumptions, evidence for/against, conflicts, confidence, uncertainty, risk flags, action class, tool trace, limits, latency, token usage, cost estimate, retry count, timeout state and terminal status.

## Observability
OpenTelemetry-first portability is preferred. Framework-specific tracing may enrich but cannot become the sole audit source. A10 owns evidence integrity; A9 owns operational health.

## Security
Least privilege; explicit allowlists; no ambient credential inheritance; secrets never enter model prompts unless a later gated design explicitly permits a bounded token; external instructions are untrusted; tool results are validated; security-sensitive tool use must be attributable.

## Retry / timeout / circuit breaker
Retries are bounded and idempotency-aware. Repeated provider/model/tool failures open a circuit breaker and enter degraded safe state rather than infinite loops.

## State
Checkpoint only workflow state needed for correctness. State versions are schema-versioned. Resume must revalidate freshness-sensitive facts before continuing.

## Cost / token / concurrency
Each contract specifies max turns, max tool calls, token and cost budgets, concurrency and a safe degradation path.

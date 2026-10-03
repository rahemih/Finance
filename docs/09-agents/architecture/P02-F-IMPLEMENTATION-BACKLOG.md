# P02-F Implementation Backlog

STATE = DEFERRED_UNTIL_P02_F

## Entry gate
P01 and G1 complete; P02-A through relevant dependencies available; P02-F explicitly active; task/lock/write scopes valid; security/dependency governance permits implementation.

## Work items
1. Revalidate OpenAI Agents SDK, LangGraph, PydanticAI, Microsoft Agent Framework, Custom orchestration, MCP and A2A against current versions, licenses, security and maturity.
2. Score governance compatibility, typed outputs, tool control, handoffs, state/checkpoints, tracing, HITL, security boundaries, recovery, cost, latency, Python/TypeScript integration, testability, lock-in, maturity, license and operational complexity.
3. Select one primary runtime; add only justified specialist components. Framework sprawl is forbidden.
4. Create ADR with rejected alternatives and exit strategy.
5. Implement typed A0–A10 runtime adapters without changing canonical authority.
6. Implement bounded specialist spawning and termination.
7. Implement state/checkpoint and resume-time freshness revalidation.
8. Implement message-envelope validation.
9. Implement A5/A8 veto enforcement as deterministic non-bypassable gates.
10. Implement prompt-injection/tool-abuse controls.
11. Implement tracing/metrics/cost/token/latency observability.
12. Implement evaluation harness and red-team suite.
13. Defer final dependency installation/version pinning to P04 governance where required.

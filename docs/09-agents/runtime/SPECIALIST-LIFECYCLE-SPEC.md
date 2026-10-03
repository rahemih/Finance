# Specialist Lifecycle & Bounded Spawning

## Lifecycle

`REQUESTED → AUTHORIZED → SPAWNED → ACTIVE → HANDOFF|COMPLETE|FAILED|CANCELED → TERMINATED`

A specialist exists only inside a parent run and inherits the strictest of:
1. Task Contract authority;
2. parent agent authority;
3. specialist catalog permissions;
4. current A5/A8 gates;
5. runtime tool policy.

## Spawn authorization

Required before spawn:
- registered specialist_id;
- canonical parent_agent match;
- explicit spawn trigger satisfied;
- finite purpose and termination condition;
- max turns/tool calls/token/cost/time budget;
- concurrency slot available;
- no active circuit breaker;
- no authority expansion.

## Hard limits

- specialist cannot create permanent agents;
- recursive specialist spawning is forbidden by default;
- depth > 1 requires explicit future contract authority and remains forbidden in this preflight;
- specialists cannot modify Task Contracts, locks, risk limits or security policy;
- specialists cannot acquire new tools or credentials;
- parent cannot use a specialist to bypass its own forbidden action.

## Termination

Terminate on success, budget exhaustion, timeout, stale critical input, parent cancellation, A5/A8 veto, circuit breaker, malformed output, unsupported handoff, or evidence/provenance failure.

Termination must emit final state, reason, consumed budgets, outputs/evidence refs and unresolved items.

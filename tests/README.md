# tests

Cross-workspace contract, integration, security, replay, deterministic-fixture and recovery test harness.

P04-E canonical foundation:
- `harness/` — reusable deterministic test primitives;
- `foundation/` — engineering-foundation unittest suite;
- `fixtures/foundation/` — small source-controlled deterministic fixtures.

Rules:
- harness code has no provider/network dependency;
- deterministic tests receive clock/IDs/replay/failure inputs explicitly;
- `TIMEOUT_UNKNOWN` is unresolved, never automatic success/rejection;
- blind retry before reconciliation is forbidden in the provider simulator;
- raw secrets/live credentials are forbidden in fixtures.

Unit tests for future production modules may remain colocated with owning code where the selected ecosystem benefits from that convention.

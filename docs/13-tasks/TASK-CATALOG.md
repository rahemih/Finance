# Task Catalog

This catalog is the canonical index of governed work.

| Task ID | Phase | Title | Risk | Status | Contract | Lock |
|---|---|---|---|---|---|---|
| FIN-P00-WA-001 | P00 | Repository foundation bootstrap | MEDIUM | CANONICAL_COMPLETE | bootstrap exception: initial governance creation | RELEASED |
| FIN-P00-WB-001 | P00 | Automated branch hygiene and naming policy | MEDIUM | ACTIVE | `contracts/tasks/FIN-P00-WB-001.json` | LOCK-FIN-P00-WB-001-01 |

## Rules

- New governed work requires a Task ID and machine-readable Task Contract.
- Task execution is forbidden when NOT_READY or BLOCKED.
- Repairs use `<TASK-ID>-RNN`.
- CANONICAL_COMPLETE requires merge, post-merge evidence, lock release, CURRENT-STATE update and catalog reconciliation.

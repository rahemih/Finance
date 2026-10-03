# Task Catalog

This catalog is the canonical index of governed work.

| Task ID | Phase | Title | Risk | Status | Contract | Lock |
|---|---|---|---|---|---|---|
| FIN-P00-WA-001 | P00 | Repository foundation bootstrap | MEDIUM | CANONICAL_COMPLETE | bootstrap exception: initial governance creation | RELEASED |
| FIN-P00-WB-001 | P00 | Automated branch hygiene and naming policy | MEDIUM | CANONICAL_COMPLETE | `contracts/tasks/FIN-P00-WB-001.json` | RELEASED |
| FIN-P00-WC-001 | P00 | Linear project activation and project-management coordination | LOW | CANONICAL_COMPLETE | `contracts/tasks/FIN-P00-WC-001.json` | RELEASED |
| FIN-P00-WD-001 | P00 | Project toolchain / plugin / skill activation matrix | MEDIUM | CANONICAL_COMPLETE | `contracts/tasks/FIN-P00-WD-001.json` | RELEASED |
| FIN-P00-WE-001 | P00 | Detailed canonical roadmap and execution roadmap | MEDIUM | CANONICAL_COMPLETE | `contracts/tasks/FIN-P00-WE-001.json` | RELEASED |

## Rules

- New governed work requires a Task ID and machine-readable Task Contract.
- Task execution is forbidden when NOT_READY or BLOCKED.
- Repairs use `<TASK-ID>-RNN`.
- CANONICAL_COMPLETE requires merge, post-merge evidence, lock release, CURRENT-STATE update and catalog reconciliation.

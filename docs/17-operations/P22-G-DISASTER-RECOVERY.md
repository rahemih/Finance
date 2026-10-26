# P22-G — Disaster Recovery

Task: `FIN-P22-WG-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Define a deterministic reference disaster-recovery orchestration contract without performing a real failover or production cutover.

## Eligibility

A disaster-recovery plan can advance only when:

- operational state is `HALTED` or `EMERGENCY`;
- the P22-F restore/rebuild drill belongs to the same canonical P22-E backup manifest;
- the drill status is `PASS` and `trusted_after_drill=true`;
- the drill mode matches the DR class;
- DR0/DR1/DR2 recovery-domain lineage remains off-primary;
- DR0 reconciliation has passed;
- explicit owner recovery authorization is present before the plan becomes `REFERENCE_RECOVERY_READY`.

Without owner authorization the plan remains `AWAITING_OWNER_AUTHORIZATION`.

## Reference sequence

The deterministic plan contains only reference steps:

1. declare disaster reference;
2. contain primary reference;
3. prepare recovery reference;
4. validate restore or rebuild reference;
5. perform DR0 execution-authority reconciliation reference when applicable;
6. await explicit owner recovery authorization;
7. mark the reference plan recovery-ready.

No step executes a runtime operation.

## Authority boundary

`REFERENCE_RECOVERY_READY` is not a production cutover command.

The contract grants no real failover, DNS/routing/load-balancer mutation, storage/database mutation, network access, credential access, runtime state mutation, external-order authority or production recovery certification.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-H — Incident / Postmortem remains NOT_STARTED until P22-G is canonically closed.

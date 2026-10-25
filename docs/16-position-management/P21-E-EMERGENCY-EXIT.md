# P21-E — Emergency Exit

Task: `FIN-P21-WE-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WE-001-01` / ACTIVE  
Dependency: P21-A through P21-D CANONICAL_COMPLETE / RELEASED

## Objective

Create deterministic reference-only emergency reduction/flatten plans without converting an emergency trigger into a Risk/Firewall/OMS bypass.

## Authority separation

P16 health or circuit-breaker output can be trigger evidence, but P16 explicitly has no position-close authority. P21-E therefore requires an explicit governed emergency authority decision.

- `EMERGENCY_REDUCE`: strictly partial and requires `A5_GOVERNED_REDUCE_ONLY` or `OWNER_EXPLICIT_EMERGENCY_REDUCE`.
- `EMERGENCY_FLATTEN`: quantity must equal the complete current open quantity and authority must be exactly `OWNER_EXPLICIT_EMERGENCY_FLATTEN`.

This preserves the architecture rule that Global Halt and Emergency Flatten are distinct actions.

## Execution uncertainty

A provider/execution incident cannot produce an emergency exit plan while execution exposure is unresolved. `PROVIDER_OR_EXECUTION_INCIDENT` requires `RESOLVED_NO_CONFLICT` reconciliation.

Blind retry and blind cross-broker reroute are forbidden. Every emitted plan states that downstream execution must remain idempotent/reduce-only and reconciliation is required before retry.

## Position binding

Requests bind to the exact current P21-A `position_record_id`. Stale records and CLOSED positions fail closed.

P21-E does not require current P21-B/P21-D protection to remain healthy because an emergency may exist precisely when normal protection is unavailable; it still never mutates canonical position state directly.

## Authority boundary

No real venue query, credentials, network I/O, external order submission/mutation, automatic OMS mutation, Risk/Firewall bypass, direct canonical-position mutation or Live execution authority is introduced.

P21-F..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

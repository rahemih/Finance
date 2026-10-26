# P21-G — Restart / Crash Recovery

Task: `FIN-P21-WG-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WG-001-01` / ACTIVE  
Dependency: P21-A through P21-F CANONICAL_COMPLETE / RELEASED

## Objective

Recover safely after process restart/crash from an exact content-addressed canonical position checkpoint plus exact P21-F reconciliation evidence.

## Recovery contract

A checkpoint must:
- reproduce the exact P21-A `position_record_id`;
- pass a content SHA-256 integrity check;
- bind to a P21-F reconciliation report for the same position record.

Recovery is only eligible when P21-F verdict is `MATCHED`.

Any mismatch remains fail-closed:
- `safe_hold_required = true`;
- `new_entry_block_required = true`;
- action = `MANUAL_GOVERNED_RECOVERY_REQUIRED`.

## Authority boundary

P21-G produces a deterministic recovery plan only. It performs no real venue query, uses no credentials/network, places or mutates no external order, automatically mutates no OMS or canonical P21-A state, and grants no Live authority.

P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

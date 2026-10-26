# P21-G — Restart / Crash Recovery

Task: `FIN-P21-WG-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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

## Canonical closure evidence

- implementation PR #445 = MERGED;
- implementation head = `7f9f90bee9cebdddd20d87e372f22a5d598a477b`;
- implementation Governance = `40307905378` / SUCCESS;
- implementation artifact = `12643463101` / `sha256:c3608f9494c3e6498be965b4785344749d90eafa9686306602dfd5040218e933`;
- deterministic P21-G evidence SHA256 = `75004d363d9540e342e7f603f8a5c7734b31b89222e4397e5c29e54cd63c1216`;
- implementation merge SHA = `0e83e9aca4fb84407f403d8727a1dcd2b9df48f2`;
- post-merge Governance = `40308187311` / SUCCESS;
- post-merge artifact = `12642289348` / `sha256:a2f03aefbfa8189514da70bb073a73a91a3d9beb4a0f02c0716f057a2886e61a`;
- post-merge Branch Hygiene = `40308187455` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-H — Position Lifecycle Tests = READY_NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-G completion certifies deterministic restart/crash recovery planning only. It does not query or mutate a real venue, automatically mutate broker/OMS/canonical state, or authorize Live trading.

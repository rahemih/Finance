# P22-B — Health / System-State Machine

Task: `FIN-P22-WB-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Define a deterministic reference state machine for operational health without granting runtime mutation or remediation authority.

## Canonical states

`NORMAL`, `DEGRADED`, `SAFE_MODE`, `HALTED`, `EMERGENCY`, `RECOVERY`.

Health snapshots are explicit caller-supplied facts with deterministic IDs, correlation lineage and bounded reason codes. P22-B does not diagnose root cause; P22-C owns diagnostics.

## Safety semantics

- EMERGENCY health always produces EMERGENCY.
- HALT_REQUIRED produces HALTED unless already EMERGENCY.
- UNSAFE produces SAFE_MODE unless the system is already HALTED or EMERGENCY.
- DEGRADED does not weaken a restricted state.
- A HEALTHY snapshot cannot automatically de-escalate SAFE_MODE/HALTED/EMERGENCY.
- Restricted states require explicit recovery authorization to enter RECOVERY.
- RECOVERY requires another healthy evaluation before NORMAL.

The module returns a deterministic decision record only. It does not mutate runtime state.

## Authority boundary

No network, credentials, diagnostics, self-healing, risk-policy relaxation, external-order authority or Live authority is granted. `LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-C remains NOT_STARTED until P22-B is canonically closed.

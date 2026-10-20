# P19-F — Paper / Live Drift Metrics

Task: `FIN-P19-WF-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: IN_PROGRESS  
Dependency: P19-A..P19-E CANONICAL_COMPLETE

## Objective

Measure deterministic drift between the P19-E modeled execution result and a governed observed-execution sample without confusing reference data, broker certification or actual Live observations.

## Observation classes

P19-F recognizes exactly three source classes:

- `REFERENCE_OBSERVATION` — deterministic engineering/reference validation only;
- `BROKER_CERTIFICATION_OBSERVATION` — future broker-simulation/certification evidence;
- `LIVE_EXECUTION_OBSERVATION` — genuine observed execution evidence.

A drift window may contain only one observation class.

The future canonical owner of actual observed latency/slippage measurements is **P20-H**. Broker certification evidence belongs to **P20-I**.

## Metrics

Every observed sample binds exactly one P19-E paper/Digital Twin sample. P19-F measures:

- fill-ratio drift;
- adverse-slippage drift;
- fee drift;
- latency drift;
- fill-status mismatch.

Each pair receives `NORMAL`, `WARN` or `FAIL` from the governed policy. A window inherits the worst pair severity.

## Live-claim boundary

`live_drift_validated=true` is possible only when all of the following are true:

1. observation class is `LIVE_EXECUTION_OBSERVATION`;
2. the governed minimum sample count is reached;
3. aggregate severity remains `NORMAL`.

Reference observations can never satisfy Live validation regardless of sample count or metric quality. Broker-certification observations also cannot satisfy Live validation.

## Canonical CI evidence

Current CI intentionally uses `REFERENCE_OBSERVATION`, created as a small deterministic perturbation of the P19-E reference result. It validates metric math and lineage only.

Therefore canonical P19-F CI must report:

- `claim_scope = REFERENCE_ONLY`;
- `live_empirical_status = UNAVAILABLE_PRE_P20_H`;
- `live_drift_validated = false`.

This is not a gap disguised as a pass: there is no governed Live execution source before P20-H, and LIVE_TRADING remains disabled.

## Safety

G10 authority: false.  
Production-readiness authority: false.  
Execution authority: false.  
Order-routing authority: false.  
P20: NOT_STARTED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

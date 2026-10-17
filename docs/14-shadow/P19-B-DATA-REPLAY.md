# P19-B — Data Replay

Task: `FIN-P19-WB-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: CANONICAL_COMPLETE  
Dependency: P19-A CANONICAL_COMPLETE

## Objective

Replay the exact historical data stream deterministically from a canonical P06-G `ReplaySnapshot` so later Decision Replay can reconstruct what information the system could have seen at each simulated time.

## Authority boundary

P06-G remains the anti-lookahead owner. P19-B does not rebuild historical queries and does not create decisions, fills, orders or broker messages.

Every replay event binds:
- sequence;
- event time;
- availability time;
- exact dataset name/version;
- entity/scope;
- canonical payload SHA-256;
- source evidence SHA-256.

## Clock semantics

The P06-G clock mode is preserved:
- `EVENT_TIME` orders by event time, then availability;
- `RECEIVE_TIME` orders by availability, then event time;
- `CONTROLLED_SIMULATION_CLOCK` uses deterministic availability-time ordering.

`replay_through(t)` first asks `ReplaySnapshot.view_at(t)` to validate the simulated time and then emits only events whose event time and availability time are no later than `t`.

Input ordering does not affect the replay result.

## Fail-closed behavior

P19-B rejects:
- dataset name/version absent from the snapshot;
- entity outside the frozen snapshot scope;
- event time outside replay/dataset windows;
- availability beyond the frozen snapshot cutoff;
- duplicate sequence or event identity;
- simulated time rejected by P06-G.

## Downstream

P19-C Decision Replay consumes the content-addressed ordered event stream from P19-B.

P19-B does not claim Decision Replay, Incident Replay, Digital Twin fill accuracy, paper/live drift validation or G10.

## Safety

Network/credentials: NONE.  
Decision authority: false.  
Fill authority: false.  
Execution authority: false.  
Order-routing authority: false.  
Broker/exchange routing: false.  
P20: NOT_STARTED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.


## Canonical closure evidence

- Implementation PR #394 = MERGED.
- Final implementation head: `22e9335d33f544a2e79866587717dde805f5f115`.
- PR Governance: `39048625186` / SUCCESS.
- PR artifact: `12106314783` / `sha256:dd534780d052f93efb5dcceaaf4c18be6b477beb23ce37b74482e5a87274b1dc`.
- Merge SHA: `828ca9047a2863cb3558343cf4d7d53e95f7eef8`.
- Post-merge Governance: `39048812613` / SUCCESS.
- Post-merge artifact: `12107295208` / `sha256:c0efde8b800cc39545798d3f1cd6c5c95001487cbea82e91140b2a75418326f7`.
- Post-merge Branch Hygiene: `39048812492` / SUCCESS.
- Lock: RELEASED.
- Next workstream: P19-C / READY_NOT_STARTED.

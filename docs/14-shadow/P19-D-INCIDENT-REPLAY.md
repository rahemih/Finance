# P19-D — Incident Replay

Task: `FIN-P19-WD-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: IN_PROGRESS  
Dependencies: P19-A..P19-C CANONICAL_COMPLETE

## Objective

Reconstruct a bounded incident context deterministically without taking ownership away from Data Replay or Decision Replay.

P19-D combines:
- point-in-time data context from P19-B;
- exact-match decision references from P19-C;
- deterministic system-state/risk/firewall/data-quality/review events;
- a content-addressed incident marker and bounded replay window.

## Window semantics

The incident marker defines detected time plus pre/post context. The total window is policy-bounded. Market/data rows are included when they became **available** inside the incident window. This preserves point-in-time semantics rather than simply filtering by market event timestamp.

P19-B remains the anti-lookahead/data owner.

## Decision ownership

P19-D accepts only P19-C references with `EXACT_MATCH`. It does not re-run or mutate decision policy. Each decision reference binds decision time, P19-C replay-result/session identity, shadow-record identity and source evidence.

## System context

System events are content-addressed and deterministically ordered by availability time, event time, sequence and identity. Event taxonomy and system-state taxonomy are governed. Future system evidence, duplicate sequence/identity and out-of-window evidence fail closed.

## Output

The incident replay root binds:
- marker/policy identity;
- bounded P19-B data event IDs;
- ordered P19-C decision reference IDs;
- ordered system event IDs;
- zero downstream authority.

P19-E Digital Twin consumes this replay context for fill/slippage simulation.

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

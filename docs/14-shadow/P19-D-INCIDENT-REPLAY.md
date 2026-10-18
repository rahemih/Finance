# P19-D — Incident Replay

Task: `FIN-P19-WD-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: CANONICAL_COMPLETE  
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

For every decision reference, P19-D explicitly separates:
- **known-at-decision** evidence: event time and availability time are both no later than the decision time;
- **retrospective discovery**: the underlying condition/event existed no later than the decision time, but its evidence became available only afterwards.

Retrospective discoveries are preserved for forensic analysis but are never injected into the historical decision context. This is the P19-D hindsight-leakage barrier.

## Output

The incident replay root binds:
- marker/policy identity;
- bounded P19-B data event IDs;
- ordered P19-C decision reference IDs;
- ordered system event IDs;
- per-decision known-at-decision and retrospective-discovery partitions;
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


## Canonical closure evidence

- Implementation PR: #398 / MERGED.
- Implementation head: `02614c8e07fd2926d920dd0e118451dc0ea966a5`.
- PR Governance: `39106542403` / SUCCESS.
- PR artifact: `12129115088` / `sha256:28bed80d5067b02e8fef268239e38b97969147283f50061535d075cac95df42f`.
- Merge SHA: `bda8be3f9bb19f8bf173b2ee688a4ba793f1bc07`.
- Post-merge Governance: `39106650351` / SUCCESS.
- Post-merge artifact: `12128931702` / `sha256:942f3da762ffceb418d685a6045d064c3be3becde8de67348bfcf5cab1b42a28`.
- Post-merge Branch Hygiene: `39106650334` / SUCCESS.
- Lock: RELEASED.
- Next workstream: P19-E / READY_NOT_STARTED.

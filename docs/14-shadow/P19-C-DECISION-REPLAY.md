# P19-C — Decision Replay

Task: `FIN-P19-WC-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: IN_PROGRESS  
Dependencies: P19-A and P19-B CANONICAL_COMPLETE

## Objective

Prove that the governed shadow decision can be reproduced exactly when the system is given the same point-in-time data stream and the same typed analytical/risk/firewall/model inputs.

P19-C does not create a new decision policy. It re-runs the canonical P19-A `ShadowDecisionLedger` against the exact visible-event prefix produced by P19-B.

## Exact-match contract

For every replay case, P19-C requires:
- exact ordered P19-B visible event IDs at the decision time;
- exact P19-A `ShadowDecisionInput.input_id`;
- exact P19-A `ShadowDecisionRecord.record_id`;
- exact disposition;
- exact previous-record chain.

Any missing/extra/reordered visible event or any input/record/disposition/chain drift fails closed.

## Canonical reference

The governed reference uses the same-run P14-H signal, P15-I risk validation, P16-H G8 firewall and canonical P17 Strategy/Model identities used by P19-A. The decision timestamp is the canonical P14 signal timestamp plus one nanosecond. P19-B supplies only events visible at that timestamp.

## Multi-decision semantics

Replay cases must be ordered by strictly increasing decision time and are replayed through one fresh P19-A shadow ledger. This preserves previous-record lineage for later incident and session replay.

## Downstream

P19-D Incident Replay consumes P19-C exact-match decision sessions and adds bounded incident context.

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

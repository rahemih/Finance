# P06-E — Macro Vintage Model

Task: `FIN-P06-WE-001`  
Linear: `HOS-199`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A3 Fundamental/Macro, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Preserve macroeconomic history exactly as it became knowable over time so backtests, replay and later intelligence cannot accidentally use a revision that was unavailable at the simulated decision time.

## Vintage contract

Every observation keeps every vintage separately:

- series ID;
- observation time;
- official/provider release time;
- NEXUS QUANT observed-at time;
- zero-based revision number;
- value and unit;
- source identity;
- P06-D source dataset version;
- P06-A raw payload SHA-256 and safe object reference;
- optional source revision ID.

No revision overwrites an earlier vintage.

## Anti-lookahead rule

A vintage is eligible for replay only when:

`release_time <= decision_time AND observed_at <= decision_time`

This distinction matters when a provider release occurred before the system actually observed/ingested it.

For a given series observation, the resolver returns the highest eligible revision. If no vintage was both released and observed yet, no value is exposed.

## Revision integrity

For each series + observation:

- revision numbering starts at zero;
- revisions are contiguous;
- release time may not move backward;
- observed-at time may not move backward;
- observed-at may never precede the vintage's release time;
- duplicate revision identities fail closed.

## Operational projection vs replay truth

`latest_projection()` is explicitly an operational/latest view.

Replay/backtesting must use `resolve()` or `snapshot_as_of()`. This prevents a latest-revised macro value from leaking backward into historical research.

## Lineage

Every vintage points to:

- a deterministic P06-D dataset version;
- exact P06-A raw payload SHA-256;
- safe raw object reference.

P06-F may later derive features from these vintages, but must retain the exact dataset/vintage cutoff.

## Safety

Production macro storage vendor: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
CANARY: DISABLED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

P06-F remains blocked until P06-E canonical closure.

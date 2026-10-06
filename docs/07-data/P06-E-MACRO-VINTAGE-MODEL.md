# P06-E — Macro Vintage Model

Task: `FIN-P06-WE-001`  
Linear: `HOS-199`  
State: CANONICAL_COMPLETE  
Implementation PR: `#143` / MERGED  
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

P06-E closure is canonical. P06-F is READY_NOT_STARTED under the existing P06 Owner authorization.

## Closure evidence

- Implementation PR: `#143` = MERGED
- Final implementation head: `4c8870a0faa6d50ca62a30002ad603f3bd2f9db5`
- Implementation merge SHA: `c047c0346aac7bd8c9f2d829ee1872ddc2d60298`
- PR Governance: `37485627547` = SUCCESS
- PR artifact digest: `sha256:eced57b49c1c6c111389240ea8f34ef030275b7c975961346f867f04a0d003a6`
- Post-merge Governance: `37485983928` = SUCCESS
- Post-merge artifact digest: `sha256:413386ec7b9e38616c052bf00750c733c23883d07cbb9f0caa4b7db36f971074`
- Post-merge Branch Hygiene: `37485984069` = SUCCESS
- Lock: RELEASED
- Canonical closure PR: `#144`

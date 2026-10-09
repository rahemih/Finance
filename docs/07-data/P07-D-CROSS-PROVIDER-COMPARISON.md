# P07-D — Cross-Provider Comparison

Task: `FIN-P07-WD-001`  
Linear: `HOS-206`  
State: CANONICAL_COMPLETE  
Lead: A2 Data  
Supporting: A0, A1, A3, A4, A8, A9, A10

## Objective

Compare independent providers only when the data is explicitly aligned and semantically comparable.

## Comparison boundary

A group is defined by the exact tuple:

`sample_id + canonical_id + metric + comparison_family`

No comparison occurs across different families. A venue trade, broker/tick proxy, futures proxy, derived index or other semantically distinct source must use a different family unless governance explicitly proves equivalence.

## Coverage

Each observation carries `coverage_bps`. Each metric/family rule declares:

- minimum independent-provider count;
- minimum coverage per eligible observation;
- explicit absolute and/or relative divergence threshold.

Observations below minimum coverage do not satisfy the provider minimum. Insufficient eligible providers fail closed.

## Divergence

Eligible providers are sorted deterministically and compared pairwise. Absolute and relative divergence are evaluated independently against explicit thresholds.

## Boundaries

P07-E owns the canonical provenance/confidence and downstream eligibility contract. P07-F owns quarantine routing.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-D closure is canonical. P07-E is READY_NOT_STARTED under the existing P07 Owner authorization.

## Closure evidence

- Implementation PR: `#158` = MERGED
- Final implementation head: `192970ce73d5d9ae1f143ac8ddb6d7c21192217b`
- Implementation merge SHA: `6a66f64a6040dbc6c4a064fd3cbcd885a90b7f63`
- PR Governance: `37958221324` = SUCCESS
- PR artifact digest: `sha256:57afd9c0a550837659440e6851a2521d1678b339ca95e1158ae0975e036dbf95`
- Post-merge Governance: `37958383698` = SUCCESS
- Post-merge artifact digest: `sha256:e0e09765a5d749dddf1cc35084bdcb2b27a3ddef8f5140e1bbcfe7f17db7aa76`
- Post-merge Branch Hygiene: `37958383669` = SUCCESS
- Lock: RELEASED
- G5_TRUSTED_DATA: NOT_EVALUATED

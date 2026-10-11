# P12-B — Rolling / Conditional Correlations

Task: `FIN-P12-WB-001`  
Linear: `HOS-253`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WB-001-01` / RELEASED  
Canonical base: `40c8ac401896cff97a3d2db59cf82a3b2641dfd4`

## Objective

Compute reproducible rolling and regime-conditional correlation evidence and encode it as P12-A observed-association edges.

## Contract

- Pearson correlation is integer-only and emitted on a signed -10000..10000 basis-point scale.
- Windows are explicit and only the latest qualifying observations are consumed.
- Conditioning uses canonical P08-G regime labels.
- Minimum sample, duplicate timestamp and zero-variance cases fail closed.
- Sampling uncertainty is descriptive metadata, not a trade probability.
- Graph output is `OBSERVED_ASSOCIATION` with `UNATTRIBUTED` attribution.
- Provenance and source dataset versions are mandatory.
- CIRA capital-flow nodes can participate in correlation evidence.
- Correlation is not causation.

## Safety

LIVE_TRADING and AUTO_TRADING remain DISABLED. No signal, risk approval or execution authority is introduced.


## Canonical closure evidence
- PR #248 merged as `ec7e703098fa51af0116bd7576dc328b325693d6`
- superseded Governance `38135715196` = FAILURE / strict Pyright unused helper / AUTO_REPAIRED
- final repaired head `fd11845b0a36bb535908c012eef5253cbdf3e7f3`
- implementation Governance `38135798150` = SUCCESS
- implementation artifact `sha256:bdb74931d91add0deb967ad613e8ca225ed39b68fd2957825f8454b8b9b9f40b`
- post-merge Governance `38135889461` = SUCCESS
- post-merge Branch Hygiene `38135889536` = SUCCESS
- P12-C = READY_NOT_STARTED

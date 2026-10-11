# P12-B — Rolling / Conditional Correlations

Task: `FIN-P12-WB-001`  
Linear: `HOS-253`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WB-001-01` / ACQUIRED  
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

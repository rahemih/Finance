# P12-C — Lead / Lag Analysis

Task: `FIN-P12-WC-001`  
Linear: `HOS-254`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WC-001-01` / RELEASED  
Canonical base: `364ee61b4ad0069eaec2ec113e880f0cca707579`

## Objective

Measure reproducible temporal precedence relationships without presenting temporal ordering as causality.

## Contract

- lag candidates are symmetric around zero;
- pairing uses exact timestamp offsets;
- positive lag means LEFT_LEADS_RIGHT;
- negative lag means RIGHT_LEADS_LEFT;
- zero lag means CONTEMPORANEOUS;
- equal-strength best lags become AMBIGUOUS with no directional graph edge;
- candidate correlation is integer-only on the signed basis-point scale;
- minimum sample and nonzero variance controls fail closed;
- optional conditioning uses canonical P08-G regime labels;
- graph output remains OBSERVED_ASSOCIATION / UNATTRIBUTED;
- provenance and source dataset versions are mandatory.

## Safety

Temporal precedence is not causation. No signal probability, risk approval or execution authority is introduced. LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- PR #250 merged as `d8d9431a21dd43edd64f098a436e2a4079700d35`
- superseded head `5a92a682790dd18f8981bed5665b902a5b0c1983`
- superseded Governance `38136479250` = FAILURE / Strict Pyright unnecessary isinstance / AUTO_REPAIRED
- final repaired head `94561aec69dd3359f0c60d5ab49a6b13a123fbdc`
- implementation Governance `38136527123` = SUCCESS
- implementation artifact `sha256:341eb9a20dd79518ad5706e3ebde4095ef5ed319b56e20617e812384b94ae797`
- post-merge Governance `38136608669` = SUCCESS
- post-merge Branch Hygiene `38136608682` = SUCCESS
- P12-D = READY_NOT_STARTED

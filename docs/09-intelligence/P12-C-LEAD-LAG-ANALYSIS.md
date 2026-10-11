# P12-C — Lead / Lag Analysis

Task: `FIN-P12-WC-001`  
Linear: `HOS-254`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WC-001-01` / ACQUIRED  
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

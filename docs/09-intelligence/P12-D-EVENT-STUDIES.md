# P12-D — Event Studies

Task: `FIN-P12-WD-001`  
Linear: `HOS-255`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WD-001-01` / ACQUIRED  
Canonical base: `787c8264b3537199a5d66e8ec15741d00b78b584`

## Objective

Measure reproducible historical market response around repeated event classes without converting temporal proximity into causal attribution.

## Contract

- explicit pre-event and post-event windows;
- strict pre < event < post ordering;
- deterministic signed basis-point response;
- deterministic mean response, dispersion and sampling uncertainty;
- minimum qualifying event count;
- canonical P08-G regime conditioning;
- unique event-instance identity and event timestamps;
- P12-A graph output remains `EVENT_CONTEXT / UNATTRIBUTED`;
- provenance SHA-256 and source dataset versions are mandatory;
- MACRO_EVENT / NEWS_EVENT / CAPITAL_FLOW / ROTATION_EPISODE contexts are supported.

## Safety

Historical event response is descriptive market-memory evidence only. Causal attribution remains P12-G. LIVE_TRADING and AUTO_TRADING remain DISABLED.

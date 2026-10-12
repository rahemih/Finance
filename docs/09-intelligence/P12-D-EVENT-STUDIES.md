# P12-D — Event Studies

Task: `FIN-P12-WD-001`  
Linear: `HOS-255`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WD-001-01` / RELEASED  
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


## Canonical closure evidence
- implementation PR #252 = MERGED
- superseded queued Governance `38137932893` = CANCELLED / superseded by final test-coverage head
- final implementation head `2acb69040910b32e2e7a6952d1195dcd06804ada`
- implementation Governance `38138140980` = SUCCESS
- implementation artifact `sha256:b581ccd9e78d2dce2a25c77c3d01e5ea8f220f31727134a742b396dc89f0362c`
- implementation merge SHA `5d76fb76da1148758b86300a5d51c969d161754f`
- post-merge Governance `38138267986` = SUCCESS
- post-merge Branch Hygiene `38138267963` = SUCCESS
- P12-E = READY_NOT_STARTED

# P12-A — Knowledge Graph Schema

Task: `FIN-P12-WA-001`  
Linear: `HOS-251`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WA-001-01` / ACQUIRED  
Canonical base: `f2af4cccdb9c6671cd7255bf02b4791e7b86784b`

## Objective

Activate P12 and establish the deterministic ontology used to retain regime-aware market relationships and historical context.

## Node ontology

- ASSET
- MARKET
- MACRO_EVENT
- NEWS_EVENT
- REGIME
- CAPITAL_FLOW
- ROTATION_EPISODE

The final two node kinds implement the planned CIRA-001 P12 extension without reopening completed P05-P11 contracts.

## Edge contract

Every relationship carries:
- bounded validity period;
- regime context compatible with canonical P08-G states;
- positive sample count;
- signed strength in basis points;
- uncertainty in basis points;
- one or more evidence families;
- one or more immutable provenance SHA-256 references;
- one or more source dataset versions;
- attribution state.

P12-A only permits `UNATTRIBUTED`. Driver/causality labels remain owned by P12-G.

## Safety

- correlation/association is not causation;
- graph relationships are descriptive evidence, not signals or orders;
- production graph vendor is NOT_SELECTED;
- canonical tests are offline;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.

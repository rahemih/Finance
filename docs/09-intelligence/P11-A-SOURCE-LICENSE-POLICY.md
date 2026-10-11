# P11-A — Source / License Policy

Task: `FIN-P11-WA-001`  
Linear: `HOS-242`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WA-001-01` / ACQUIRED  
Canonical base: `c72d34bff0099eaa429fc105b447f4e60c2a2588`

## Objective

Turn news-source intake into an explicit, attributable and license-aware contract before any P11 ingestion, sentiment or narrative logic is allowed to consume it.

## Canonical rules

- Every source has an explicit source class, URL, access state, license state and attribution.
- Source URLs are credential-free HTTPS.
- Published time and observed time are both required; future publication relative to observation fails closed.
- Community/social information cannot be treated as confirmed without corroborating source IDs.
- CORROBORATED requires explicit corroboration.
- UNCONFIRMED news has zero trade authority.
- In fact, P11-A grants no direct trade/order authority at all; later signal/risk phases remain authoritative.
- Canonical tests are offline and deterministic.
- No production news vendor or paid entitlement is selected in P11-A.

## Source classes

`OFFICIAL`, `WIRE`, `NEWSROOM`, `AGGREGATOR`, `COMMUNITY`, `SOCIAL`.

## Licensing boundary

The canonical license states distinguish public reuse, attribution-required usage, internal-analysis-only usage, redistribution restrictions and unresolved license review. Downstream ingestion must not silently convert a restricted source into redistributable content.

## Safety

- LIVE_TRADING: DISABLED
- AUTO_TRADING: DISABLED
- country assumption: NONE
- credentials: NONE
- production news vendor: NOT_SELECTED

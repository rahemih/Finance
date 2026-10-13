# P13-B — Best Trading Time Engine

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P13-WB-001`  
Linear: `HOS-262`

## Objective

Evaluate historical timing-window quality for one asset/strategy/timeframe/regime comparison set and identify the strongest governed timing window without converting timing quality into signal probability, opportunity ranking, no-trade authority, risk approval or execution.

## Canonical model

Each timing window carries:
- asset, strategy, timeframe and regime identity;
- session labels;
- sample count;
- historical mean edge in signed basis points;
- uncertainty in unsigned basis points;
- open/closed market context.

The conservative adjusted edge is:

`adjusted_edge_bps = mean_edge_bps - uncertainty_bps`

Classes:
- PREFERRED;
- STANDARD;
- WEAK;
- INSUFFICIENT_EVIDENCE;
- CLOSED_CONTEXT.

Best-window selection is allowed only inside one homogeneous asset/strategy/timeframe/regime set. Cross-asset or cross-setup opportunity ranking remains P13-D.

## Guardrails

- insufficient sample or excessive uncertainty is not usable evidence;
- closed market context is never preferred;
- P13-B does not emit hard NO_TRADE;
- timing quality is not probability;
- no risk approval or execution authority;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

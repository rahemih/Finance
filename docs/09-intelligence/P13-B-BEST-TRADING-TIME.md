# P13-B — Best Trading Time Engine

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WB-001`  
Linear: `HOS-262`  
Lock: `LOCK-FIN-P13-WB-001-01` / RELEASED

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


## Canonical closure evidence

- implementation PR #267 = MERGED
- implementation head `0172ba32317ef0ffbadd955d0fafe63937a1cfd0`
- implementation Governance `38371472503` = SUCCESS
- implementation artifact `sha256:8e5634f1c7bf934baea678c4bfbd495e8454dec792d98ccf7295bcbbbf32b36b`
- implementation merge SHA `daafaa603b91028b8e1dbd755a9d8774b623eb96`
- post-merge Governance `38371665584` = SUCCESS
- Branch Hygiene `38371666341` = SUCCESS
- implementation branch = DELETED
- P13-C = READY_NOT_STARTED

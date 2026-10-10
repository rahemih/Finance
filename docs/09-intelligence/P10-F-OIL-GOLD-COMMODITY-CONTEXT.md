# P10-F — Oil / Gold / Commodity Context

Task: FIN-P10-WF-001
Linear: HOS-239
State: CANONICAL_COMPLETE
Lock: RELEASED

P10-F builds deterministic point-in-time fundamental context for crude oil and gold from the official-source registry and P06-E macro vintages.

Oil metrics cover inventory, supply and demand. Oil balance is descriptive supply minus demand and requires matched geography and unit.

Gold metrics cover supply, demand, ETF holdings, reserves and LBMA clearing volume. WGC/LBMA licensing and transport states remain governed by P10-A; P10-F does not claim production entitlement or activate credentials.

All latest values are resolved strictly as-of decision time. Later revisions cannot leak backward into historical context.

These values are descriptive only. P10-F does not infer bullish/bearish direction, price forecasts, causal market impact, signal probability, Risk approval or execution authority.

Production source mapping: NOT_SELECTED.
Country assumption: NONE.
LIVE_TRADING: DISABLED.
AUTO_TRADING: DISABLED.

## Canonical implementation evidence

- Implementation PR: #216 = MERGED
- Final implementation head: `e538e18db563033fc8aa891ba1c2e52a6e9eea9f`
- Implementation merge SHA: `6a8590c2c5f4d354c7c08009bf7da81b0926fd28`
- PR Governance: `38081533834` = SUCCESS
- PR artifact: `sha256:d09bd63005ac86d72ccf3e19f07013f40a2b039d2bdd6cc93b5965100e9e3d7b`
- Post-merge Governance: `38081618578` = SUCCESS
- Post-merge artifact: `sha256:8939f8c3b5f7af7d86842111e25b2fb0497933e120cb6cb80e404d34ac24ab13`
- Post-merge Branch Hygiene: `38081618539` = SUCCESS

P10-G becomes READY_NOT_STARTED.

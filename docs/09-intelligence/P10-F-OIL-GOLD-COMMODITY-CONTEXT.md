# P10-F — Oil / Gold / Commodity Context

Task: FIN-P10-WF-001
Linear: HOS-239
State: IMPLEMENTATION_ACTIVE
Lock: LOCK-FIN-P10-WF-001-01 / ACQUIRED

P10-F builds deterministic point-in-time fundamental context for crude oil and gold from the official-source registry and P06-E macro vintages.

Oil metrics cover inventory, supply and demand. Oil balance is descriptive supply minus demand and requires matched geography and unit.

Gold metrics cover supply, demand, ETF holdings, reserves and LBMA clearing volume. WGC/LBMA licensing and transport states remain governed by P10-A; P10-F does not claim production entitlement or activate credentials.

All latest values are resolved strictly as-of decision time. Later revisions cannot leak backward into historical context.

These values are descriptive only. P10-F does not infer bullish/bearish direction, price forecasts, causal market impact, signal probability, Risk approval or execution authority.

Production source mapping: NOT_SELECTED.
Country assumption: NONE.
LIVE_TRADING: DISABLED.
AUTO_TRADING: DISABLED.

Next after canonical closure: P10-G — Crypto Fundamental / On-Chain Context.

# P10-E — Rates / Yields / Currency Macro

Task: FIN-P10-WE-001
Linear: HOS-238
State: IMPLEMENTATION_ACTIVE
Lock: LOCK-FIN-P10-WE-001-01 / ACQUIRED

P10-E builds deterministic point-in-time context for policy rates, sovereign yields and cross-currency rate/yield differentials.

Allowed metric kinds are POLICY_RATE and GOVERNMENT_YIELD. Unit is PERCENT. Reference official source identities are FRED_ALFRED, ECB, BOE, BOJ and BIS, and every source must also exist in the P10-A registry.

The latest-as-of rule allows only observations and revisions whose release and observed-at timestamps are not after decision time.

Yield-curve spread is longer tenor minus shorter tenor for the same currency, jurisdiction and unit.

Currency macro differential is base minus quote. The currencies must differ; metric kind and unit must match; yield comparisons require matched tenor.

These values are descriptive only. P10-E does not infer bullish/bearish direction, carry recommendations, price forecasts, signal probability, Risk approval or execution authority.

Production source mapping: NOT_SELECTED.
Country assumption: NONE.
LIVE_TRADING: DISABLED.
AUTO_TRADING: DISABLED.

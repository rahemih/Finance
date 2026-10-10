# P10-E — Rates / Yields / Currency Macro

Task: FIN-P10-WE-001
Linear: HOS-238
State: CANONICAL_COMPLETE
Lock: RELEASED

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


## Canonical closure evidence

- Implementation PR: `#214` = MERGED
- Final implementation head: `d1147464fa147dbaabef33e9cafbcd4a4eedd80b`
- Implementation merge SHA: `7f11dc864459a67d01970286cb2724f3fd12bb51`
- PR Governance: `38080122549` = SUCCESS
- PR artifact: `sha256:44c9b1ed3018ec2400ca4ab45b225fb00069ddbcb331b2a67ac836a823587b6f`
- Post-merge Governance: `38080508977` = SUCCESS
- Post-merge artifact: `sha256:a832045023a10eb650b1adeb104dcd814a373e6bf21a9a3dd8dd5b1078bfd684`
- Post-merge Branch Hygiene: `38080508982` = SUCCESS

The initial queued PR Governance run `38079423916` executed no test step and was superseded by the final-head run after explicit deterministic payload serialization hardening. No safety, data or trading semantics were weakened.

P10-F becomes `READY_NOT_STARTED`.

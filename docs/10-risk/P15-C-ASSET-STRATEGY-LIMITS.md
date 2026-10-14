# P15-C — Asset / Strategy Limits

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WC-001`

P15-C applies explicit hard limits at ASSET and STRATEGY scope after P15-B sizing.

Rules are governed inputs; there are no production numeric defaults. Each evaluation requires:
- an explicit asset rule;
- an explicit strategy rule;
- explicit current usage for both scopes;
- upstream `SIZE_CANDIDATE`.

The engine checks incremental risk-budget usage and open-position counts. Missing rules, missing usage, disabled rules or exceeded limits veto new risk.

A positive `LIMITS_ELIGIBLE` result does not perform portfolio/correlation checks, leverage approval or execution.

P15-D..P15-I = NOT_STARTED.  
P16 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

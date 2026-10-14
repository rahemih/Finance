# P15-C — Asset / Strategy Limits

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- PR #307 = MERGED;
- implementation head = `907b73152bfabcb933ac70a7c6e1bcc57a7265ee`;
- Governance = `38526638542` / SUCCESS;
- artifact = `sha256:5015c19d10732264e8212da4a024b84a687ddd0a547ac819e765d6d459dd1451`;
- implementation merge = `f3bcff6c40cee0b82a75609b6729d880f75aa14c`;
- `FIN-P15-WC-001` = CANONICAL_COMPLETE;
- lock = RELEASED;
- P15-D = READY_NOT_STARTED;
- P15-E..P15-I = NOT_STARTED;
- P16 = NOT_STARTED.

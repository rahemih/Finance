# P17-G — Strategy Registry

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WG-001`

## Objective

Provide an immutable deterministic registry for strategy versions and their P17 validation lineage.

Each strategy version binds:
- strategy/version identity;
- definition, code and config SHA-256;
- explicit universe and timeframe;
- optional P17-D/E/F validation certificates.

A `VALIDATED` strategy requires all three P17-D/E/F certificate references.

## Immutability

The same `strategy_id + version` may be registered repeatedly only when the canonical record is byte-equivalent. Divergent content under the same version fails closed.

## Authority boundary

The registry does not:
- promote a strategy automatically;
- claim profitability;
- pass G9;
- route or execute orders;
- start P18.

P17-H..P17-I remain later workstreams.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

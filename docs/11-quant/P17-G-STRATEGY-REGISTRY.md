# P17-G — Strategy Registry

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- implementation PR #354 = MERGED;
- implementation head = `25f255f312ffe17091d43085926c0fc9c1da5c9f`;
- Governance `39008606942` = SUCCESS;
- artifact = `sha256:956457f99ba648812f3bfb231f2521820dd619a30fc8277122c92cf7d2cdc19e`;
- implementation merge = `c66d0118ae289a62a19dd1c90b3833c7918d1a8b`;
- `FIN-P17-WG-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P17-WG-001-01` = RELEASED;
- P17-H = READY_NOT_STARTED;
- P17-I = NOT_STARTED;
- `G9_QUANT_VALIDATED` = NOT_REACHED.

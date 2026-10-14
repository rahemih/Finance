# P16-C — Size / Leverage / Exposure Check

State: CANONICAL_COMPLETE  
Task: `FIN-P16-WC-001`

## Objective

Revalidate the final execution-intent risk envelope immediately before later pre-trade checks using canonical P15 decisions rather than inventing a second risk policy.

P16-C consumes:
- P15-B candidate position size;
- P15-D portfolio/correlation exposure result;
- P15-E leverage/margin result;
- P15-H defensive mode;
- P15-I independent-validation PASS.

## Rules

- P16-B VETO is non-bypassable;
- P15-I must be `P15_INDEPENDENT_RISK_VALIDATION / PASS`;
- final quantity may not exceed the P15-B candidate after applying P15-H `risk_scale_bps`;
- final quantity must align to the explicit quantity step;
- final gross/net/correlated-cluster exposure may not exceed the envelope analyzed by P15-D;
- final leverage and margin utilization may not exceed the envelope analyzed by P15-E;
- any authority escalation in imported P15 decisions vetoes the request.

## Boundary

A positive result is `PRETRADE_C_ELIGIBLE` only.

P16-C does not recompute P15 risk policy, create orders, route to a venue, execute trades or grant G8.

P16-D..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #327 = MERGED;
- implementation head = `d7b4e72bee5a89a4fab556dcddd20936c0fd474b`;
- Governance `38568572787` = SUCCESS;
- artifact = `sha256:fe325e366e30e2541527bb392595855ea9ad14f61d5b2a872758d88d195c1acf`;
- implementation merge = `7793d255535759002d3a0c90170882a08c6bdbef`;
- `FIN-P16-WC-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WC-001-01` = RELEASED;
- P16-D = READY_NOT_STARTED;
- P16-E..P16-H = NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED.

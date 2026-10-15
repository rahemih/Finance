# P16-C — Size / Leverage / Exposure Check

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P16-WC-001`

## Objective

Revalidate the final pre-trade intent against the canonical P15 approvals immediately before later firewall checks.

P16-C does **not** recompute P15 risk algorithms. Instead it rejects risk-increase drift after those approvals.

## Canonical approval sources

- P15-B — approved candidate quantity;
- P15-D — approved post-candidate gross, absolute-net and correlated-cluster exposure metrics;
- P15-E — approved post-candidate leverage and margin-utilization metrics.

All three P15 decisions must remain eligible.

## Rule

Equal or lower-risk final values may proceed.

Any final value above its corresponding canonical P15 approval is a VETO:
- size;
- gross exposure;
- absolute net exposure;
- correlated-cluster exposure;
- leverage;
- margin utilization.

P16-B VETO remains non-bypassable.

## Boundary

Positive output is `PRETRADE_C_ELIGIBLE` only.

P16-D..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
No order-routing or execution authority exists here.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

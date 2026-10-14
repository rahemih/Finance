# P15-G — Counterparty / Capital Segmentation

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WG-001`

## Objective

Constrain capital allocation by explicit counterparty and capital-segment ceilings after P15-F.

All allocations are basis points of governed total capital.

## Rules

- every counterparty must have an explicit rule;
- every capital segment must have an explicit rule;
- total allocation after the candidate may not exceed 10000 bps;
- counterparty allocation may not exceed its governed ceiling;
- segment allocation may not exceed its governed ceiling;
- P15-F `VETO` is non-bypassable;
- P15-F `DE_RISK_REQUIRED` is preserved for P15-H.

## Boundary

P15-G does not select a venue, route an order or execute a trade.  
P15-H owns defensive-mode selection.  
P15-I owns independent integrated validation.  
P16 remains NOT_STARTED.

Production numeric defaults: **NONE**.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

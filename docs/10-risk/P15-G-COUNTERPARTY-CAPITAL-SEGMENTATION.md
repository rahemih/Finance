# P15-G — Counterparty / Capital Segmentation

State: CANONICAL_COMPLETE  
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


## Canonical closure evidence

- implementation PR #316 = MERGED;
- implementation head = `5e636686adc5fa082167b08248f9a27aed265a22`;
- Governance `38532052913` = SUCCESS;
- artifact = `sha256:4438fa3b17de9e3700bbc8e3fc7c224a3a472d6d5f67ade6a04ef64b214f5dce`;
- implementation merge = `57bda0d5cff748d859a64db8b5dc9c06581f8398`;
- `FIN-P15-WG-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P15-WG-001-01` = RELEASED;
- P15-H = READY_NOT_STARTED;
- P15-I = NOT_STARTED;
- P16 = NOT_STARTED.

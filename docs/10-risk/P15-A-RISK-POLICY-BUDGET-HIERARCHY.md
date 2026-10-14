# P15-A — Risk Policy / Budget Hierarchy

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WA-001`  
Linear: `NEXUS QUANT — Management Control & Reporting Register-1`

## Objective

Establish the first independent P15 risk-control layer: a finite hierarchical risk-budget contract that downstream work cannot silently exceed or relax.

## Budget semantics

The hierarchy uses **basis points of one governed total risk budget**, not dollars and not position notional.

The root `GLOBAL` node is therefore structurally `10000 bps` = 100% of whatever total risk budget is approved by governed policy. P15-A deliberately does **not** invent the monetary size of that total risk budget.

Production monetary ceiling: **UNSET / EXPLICIT GOVERNED POLICY REQUIRED**.

Production numeric defaults: **NONE**.

## Hierarchy

Canonical scope order:

`GLOBAL → PORTFOLIO → MARKET → ASSET → STRATEGY → TRADE`

Rules:

- exactly one GLOBAL root;
- every non-root node has an existing upstream parent;
- a child may never have a budget above its parent;
- direct children may not collectively be delegated more budget than their parent;
- all node budgets are explicit;
- disabled nodes veto new risk;
- risk consumption that exceeds remaining budget at any ancestor is vetoed;
- policy identity and decisions are deterministic and reproducible.

## Independent risk authority

A5 Risk owns the veto path.

A5 may reject additional risk but may not:

- silently increase or rewrite its own ceilings;
- calculate final position quantity in P15-A;
- choose leverage in P15-A;
- emit broker/exchange orders;
- bypass P16 Pre-Trade Risk Firewall.

A positive P15-A result is named `POLICY_CAPACITY_ELIGIBLE`. It is **not** position-size approval and is **not** execution approval.

## Phase boundaries

Still NOT_STARTED:

- P15-B — Position Sizing
- P15-C — Asset / Strategy Limits
- P15-D — Portfolio / Correlation Exposure
- P15-E — Leverage / Margin
- P15-F — Drawdown / Risk-of-Ruin
- P15-G — Counterparty / Capital Segmentation
- P15-H — Defensive / De-Risk Modes
- P15-I — Independent Risk Validation
- P16 — Pre-Trade Risk Firewall

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

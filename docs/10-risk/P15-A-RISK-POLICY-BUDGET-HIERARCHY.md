# P15-A — Risk Policy / Budget Hierarchy

State: CANONICAL_COMPLETE  
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

Next workstream:

- P15-B — Position Sizing = READY_NOT_STARTED

Still NOT_STARTED:

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


## Canonical closure evidence

Implementation:
- PR #302 = MERGED;
- final implementation head = `e41055e256e675ce6d9fc3055470f0d754dc5c6a`;
- PR Governance = `38524129028` / SUCCESS;
- implementation artifact = `sha256:625e1c2d3d6a2048291efc3eae19eb28244f6dfbb4c7d79d4dd15c384044b3b1`;
- implementation merge = `ecfafbfdc10b6354dff5ff84e6426c349db49e3b`;
- canonical implementation branch `feat/FIN-P15-WA-001-risk-policy-budget-hierarchy` = DELETED after merge;
- superseded preflight branch `risk/FIN-P15-WA-001-risk-policy-budget-hierarchy` = NO PR / NON_CANONICAL.

Closure state:
- `FIN-P15-WA-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P15-WA-001-01` = RELEASED;
- P15-B = READY_NOT_STARTED;
- P15-C..P15-I = NOT_STARTED;
- P16 = NOT_STARTED;
- closure PR #303 independent revalidation Governance = `38524603270` / SUCCESS;
- closure revalidation artifact = `sha256:8fc6e2219910a9dac4740d99af8a940ffda027135ca9656af9c4b11b5d6874fa`;
- final closure-head Governance after recording this evidence = REQUIRED_BEFORE_MERGE.

Safety remains unchanged:
- production monetary risk ceiling = UNSET;
- position sizing authority = NONE;
- leverage-selection authority = NONE;
- execution authority = NONE;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

# NEXUS QUANT — Risk / Firewall / Execution Architecture

STATE = P02-E BASELINE  
TASK = `FIN-P02-WE-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Define the non-bypassable path from a non-executable SignalCandidate to provider execution:

`SignalCandidate → Risk → ProposedTradeIntent → Pre-Trade Firewall → ApprovedTradeIntent → OMS → RouteAttempt → Execution Adapter → Provider → Reconciliation`

No strategy, model, agent or UX component can skip this chain.

## 2. Independent Risk Engine

Owner: **A5**

Risk consumes:
- SignalCandidate;
- calibrated probability or unavailable state;
- data-quality/freshness;
- current positions;
- open and uncertain orders;
- portfolio exposure;
- leverage/margin;
- drawdown/daily-loss state;
- liquidity/spread/slippage context;
- concentration/correlation;
- counterparty/provider exposure;
- system/provider health;
- risk-policy version.

Risk decisions:
- `ALLOW_WITH_LIMITS`
- `REDUCE`
- `REJECT`
- `HALT_SCOPE`

Risk may reduce or reject.

Risk may not:
- increase its own ceilings;
- submit broker orders;
- bypass Firewall;
- override Security halt.

Numerical production limits are deferred to P15.

## 3. RiskVerdict

A RiskVerdict includes:
- verdict ID;
- signal ID;
- portfolio scope;
- policy version;
- evaluated-at / valid-until;
- referenced state snapshots;
- maximum allowed quantity/notional;
- exposure constraints;
- reduce-only requirement;
- reason codes;
- risk-metrics snapshot reference.

An expired RiskVerdict is invalid.

## 4. ProposedTradeIntent

A deterministic intent-construction step uses:
- SignalCandidate;
- RiskVerdict;
- requested action context.

It produces a provider-neutral ProposedTradeIntent.

Required concepts:
- stable `intent_id`;
- environment;
- portfolio/account scope;
- canonical instrument ID;
- side;
- quantity/notional;
- order semantics;
- reduce-only;
- signal reference;
- RiskVerdict reference;
- creation/expiry;
- correlation ID.

Provider-specific symbols/order IDs do not appear here.

Quantity can be reduced to Risk-authorized size; it cannot be increased.

## 5. Pre-Trade Firewall

Owner: **A5**

The Firewall is deterministic and final before OMS.

It verifies at least:
- signal not expired;
- RiskVerdict current and valid;
- size within Risk limit;
- data quality/freshness;
- system/provider health;
- environment/account binding;
- kill-switch state;
- instrument/provider capability;
- order precision/minimums;
- duplicate/idempotency state;
- no unresolved conflicting order;
- fresh positions/open-orders state;
- post-trade exposure;
- liquidity/spread/slippage hard bounds where configured;
- credential capability;
- market/session/trading status.

Firewall outputs:
- APPROVE
- REJECT
- HALT_SCOPE

Critical unknown state fails closed.

## 6. ApprovedTradeIntent

Only an unexpired ApprovedTradeIntent may enter OMS.

It contains:
- intent ID;
- FirewallVerdict reference;
- RiskVerdict reference;
- environment/account scope;
- canonical instrument;
- side;
- approved size;
- order semantics;
- reduce-only;
- expiry;
- idempotency key;
- correlation ID.

It remains provider-neutral.

## 7. OMS

Owner: **A6**

OMS owns:
- routing;
- provider client-order-ID mapping;
- idempotent submit/cancel/replace;
- order lifecycle;
- fills;
- order/position projections;
- timeout/crash recovery;
- reconciliation.

Canonical states:

- APPROVED
- ROUTING
- SUBMITTING
- ACKNOWLEDGED
- PARTIALLY_FILLED
- FILLED
- CANCEL_PENDING
- CANCELED
- REJECTED
- EXPIRED
- UNKNOWN
- RECONCILING
- FAILED_FINAL

### Critical rule

`UNKNOWN` means the system cannot prove whether the provider accepted/executed the order.

It is neither success nor rejection.

While execution status is UNKNOWN:
- do not blindly retry;
- do not route the same exposure to another broker;
- reconcile first.

## 8. Idempotency and duplicate prevention

Identity hierarchy:

- `intent_id` — logical trade intent;
- `route_attempt_id` — one provider routing attempt;
- provider client-order-ID — provider-facing idempotency identity;
- `correlation_id` — full decision/execution trace.

Rules:
- a timeout does not create a new logical intent;
- safe retry uses the same idempotency semantics where supported;
- only one unresolved execution-capable route is allowed per intent/exposure by default;
- cross-broker reroute is forbidden while prior execution status is unknown.

## 9. Reconciliation

Triggers:
- startup/restart;
- reconnect;
- submit timeout;
- UNKNOWN state;
- provider incident recovery;
- scheduled periodic check;
- local/provider mismatch;
- before controlled provider failover.

Queries include:
- open orders;
- recent order history;
- fills/trades;
- positions;
- balances/margin/account state.

Authority:
- provider/exchange is authoritative for actual external execution facts;
- NEXUS QUANT is authoritative for original intent, Risk/Firewall decisions and audit history.

Mismatch:
- creates ReconciliationEvidence;
- blocks unsafe new execution for affected scope;
- never silently rewrites audit history.

## 10. Provider failover

Automatic blind Live cross-broker failover is forbidden.

Safe sequence:
1. detect provider degradation;
2. halt affected new intents;
3. classify all in-flight attempts;
4. reconcile;
5. resolve UNKNOWN states;
6. recompute portfolio/risk state;
7. validate certified backup;
8. obtain fresh Risk/Firewall approval;
9. route only resolved/new exposure.

A missing acknowledgement is never treated as proof of non-execution.

## 11. Kill switches

Scopes:
- STRATEGY
- INSTRUMENT
- ASSET_CLASS_OR_MARKET
- PROVIDER_OR_BROKER
- ACCOUNT
- NEW_ORDERS
- REDUCE_ONLY
- GLOBAL_HALT
- EMERGENCY_FLATTEN

Authorities include:
- A5 Risk — risk halt/reduce-only/new-orders controls;
- A6 Execution — provider self-halt on uncertainty/reconciliation failure;
- A8 Security — security halt / credential revocation;
- A9 Operations — operational halt/safe-mode request;
- Owner — Global Halt and explicitly configured Emergency Flatten.

Rules:
- halting is easier than re-enabling;
- recovery never raises risk ceilings;
- re-enable requires health/reconciliation/authorization checks;
- Emergency Flatten is not equivalent to Global Halt;
- every transition is audited.

## 12. System states

Execution behavior understands:
- NORMAL
- DEGRADED
- SAFE_MODE
- HALTED
- EMERGENCY
- RECOVERY

SAFE_MODE generally permits only explicitly allowed defensive/reduce actions.

RECOVERY requires reconciliation and health validation before return to NORMAL.

## 13. Environment binding

Approved intents and credentials are environment-bound.

Environments:
- DEV
- TEST
- RESEARCH
- DEMO
- SHADOW
- CANARY
- LIVE

Rules:
- SHADOW cannot emit live broker commands;
- DEMO routes only to simulation/practice;
- CANARY/LIVE remain disabled until later gates;
- credentials cannot silently cross environments.

## 14. Credential security

Owner: **A8**

Execution receives credential handles/references, not raw secrets in ordinary contracts.

Required principles:
- least privilege;
- trading-only where possible;
- withdrawal/transfer permission disabled/not requested where separable;
- environment/account/provider scoping;
- revocation path;
- compromise triggers security halt.

## 15. Audit trace

Every material execution outcome links:

- SignalCandidate
- RiskVerdict
- ProposedTradeIntent
- FirewallVerdict
- ApprovedTradeIntent
- route attempts
- provider ack/reject
- fills/cancels
- reconciliation
- kill switches / system-state changes
- actor/agent/policy/config versions

A single correlation ID must make the path reconstructable without exposing secrets.

## 16. Deferred implementation

P15:
- numerical portfolio limits;
- risk-of-ruin;
- allocation/correlation/counterparty models.

P16:
- actual firewall rules/thresholds and independent tests.

P20:
- provider adapters;
- OMS runtime;
- execution certification.

P21:
- position management;
- trailing/break-even/expiry/close logic.

P22:
- diagnostics/recovery runbooks.

P24:
- canary/live capital activation.

## 17. Safety

Accounts = NONE  
Credentials = NONE  
Funding = NONE  
Orders = NONE  
Demo Trading = NOT_STARTED  
Shadow Trading = NOT_STARTED  
Live Trading = DISABLED  
Auto Trading = DISABLED

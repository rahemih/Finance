# ADR-0010 — Independent Risk, Deterministic Firewall & Reconciled OMS

Status: ACCEPTED  
Task: `FIN-P02-WE-001`

## Context

A signal can be valid analytically and still be unsafe to execute because of portfolio exposure, stale account state, data quality, liquidity, provider health, duplicate-order risk or uncertain prior execution.

Execution systems are especially dangerous when network timeouts are interpreted as order rejection or when failover sends the same exposure to a second broker before the first order is reconciled.

## Decision

Adopt a non-bypassable authority chain:

`SignalCandidate → RiskVerdict → ProposedTradeIntent → Pre-Trade Firewall → ApprovedTradeIntent → OMS → Provider Adapter → Provider → Reconciliation`

### Risk

Risk is an independent veto/reduction authority.

It can:
- allow with bounded limits;
- reduce;
- reject;
- halt a scope.

It cannot:
- increase its own ceilings;
- send broker orders;
- bypass Firewall.

### Firewall

Pre-Trade Firewall is deterministic and final before OMS.

Missing/stale/unknown critical state fails closed.

### OMS

OMS owns idempotent provider routing and explicitly models `UNKNOWN` and `RECONCILING`.

A local timeout does not prove an order was rejected.

An unresolved execution-capable route blocks blind retry/reroute of the same exposure.

### Reconciliation

External venue truth is authoritative for actual fills/orders/positions.

Local intent/Risk/Firewall/audit history remains immutable.

### Failover

Blind automatic Live cross-broker order replay is forbidden.

Failover requires:
- halt;
- reconcile;
- resolve uncertain exposure;
- recompute Risk;
- fresh Firewall approval.

### Kill switches

Hierarchical kill switches are explicit and auditable.

`GLOBAL_HALT` and `EMERGENCY_FLATTEN` are distinct because flattening positions itself creates execution/market risk.

## Alternatives considered

### Strategy performs its own risk checks and sends orders
Rejected because the component requesting risk cannot be the only authority that approves it.

### OMS retries a timed-out order as a new order
Rejected because the original order may already exist/fill.

### Automatic reroute to backup broker on timeout
Rejected because it can duplicate exposure.

### One global emergency action for halt and close-all
Rejected because stopping new risk and liquidating existing risk have different consequences.

## Consequences

Positive:
- independent safety authority;
- deterministic duplicate prevention;
- recoverable crash/network behavior;
- provider portability;
- auditability;
- controlled failover.

Negative:
- more state-machine complexity;
- more reconciliation queries/evidence;
- some opportunities will be intentionally missed while uncertainty is resolved.

Missing a trade is preferable to duplicating unknown exposure.

## Risks / mitigations

Risk: RiskVerdict becomes stale between decision and execution.  
Mitigation: TTL/version/freshness checks in Firewall.

Risk: local and provider state diverge.  
Mitigation: block affected execution scope and reconcile.

Risk: partial fills create incorrect reroute quantity.  
Mitigation: recompute remaining exposure and re-run Risk/Firewall where material.

Risk: recovery operator accidentally increases authority.  
Mitigation: recovery cannot raise Risk ceilings; high-scope re-enable is governed/audited.

Risk: compromised credential.  
Mitigation: least privilege, withdrawal-disabled credentials, security halt/revocation.

## Validation / evidence

P15 validates Risk models/limits.

P16 validates independent Firewall rules and fail-closed behavior.

P20 validates OMS state machine, idempotency, provider adapters and reconciliation.

P22 validates crash/provider-outage/recovery scenarios.

P24 validates canary/live activation gates.

## Rollback / supersession

Implementation details may evolve, but the following guarantees cannot be removed without explicit supersession and A5/A6/A8/A9/A10 review:

- independent Risk veto;
- deterministic Firewall;
- stable idempotency identity;
- UNKNOWN/RECONCILING execution states;
- no blind cross-broker replay;
- audited hierarchical kill switches.

## Related tasks / gates

P02-E, P15, P16, P20, P21, P22, P24, G2, G8, G11, G12, G13.

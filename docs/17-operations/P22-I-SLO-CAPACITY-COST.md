# P22-I — SLO / Capacity / Cost Monitoring

Task: `FIN-P22-WI-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Provide deterministic, vendor-neutral reference monitoring for operational latency SLOs, capacity pressure and cost guardrails without inventing production SLAs or an Owner budget.

## Canonical lineage

P22-I inherits its reference envelopes from `docs/04-architecture/capacity-cost-envelope.json` and its fail-closed monitoring principles from P07-G.

Canonical internal latency objectives:

- `L_FAST_DATA`: p95 <= 250 ms, p99 <= 1000 ms;
- `L_SIGNAL_STANDARD`: p95 <= 2000 ms;
- `L_RISK_FIREWALL`: p95 <= 100 ms, p99 <= 250 ms;
- `L_OMS_DISPATCH`: p95 <= 100 ms;
- `L_UI`: p95 <= 2000 ms.

Three explicit consecutive miss windows require architecture review.

## Capacity monitoring

OPERATING envelope:
- average events/s = 2,000;
- peak events/s = 20,000;
- active streams = 75;
- concurrent agent runs = 10.

STRESS envelope:
- average events/s = 10,000;
- peak events/s = 50,000;
- active streams = 200;
- concurrent agent runs = 25.

At 70% of the OPERATING envelope, P22-I emits a capacity-review recommendation. Reaching the STRESS boundary is CRITICAL and requires architecture review. No automatic scaling is performed.

## Cost monitoring

No monthly cost budget is embedded in policy. The monthly budget must be supplied explicitly by the caller.

Reference budget guardrails:
- 70%: alert and forecast review;
- 85%: recommend deferring/throttling discretionary research;
- 100%: recommend freezing discretionary new research spend;
- daily cost >= 2x an explicitly supplied expected daily baseline: investigate and recommend circuit-breaking optional AI/research workloads.

These are recommendations only. Risk, Firewall, Security, Audit, Reconciliation and Kill Switch workloads remain protected from automatic cost shedding.

## Authority boundary

P22-I does not select or provision an observability vendor, certify production SLA performance, scale infrastructure, shed workloads, throttle safety-critical workloads, mutate network/runtime state, access credentials, mutate external orders or grant Live authority.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-J — Operations Validation Gate remains NOT_STARTED until P22-I is canonically closed.

# P22-I — SLO / Capacity / Cost Monitoring

Task: `FIN-P22-WI-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Provide deterministic vendor-neutral operational monitoring for canonical latency SLOs, capacity envelopes and cost guardrails without inventing production SLAs or Owner budget values.

## SLO lineage

P22-I reuses the P02 architecture latency classes exactly:

- `L_FAST_DATA`: p95 <= 250 ms, p99 <= 1000 ms;
- `L_SIGNAL_STANDARD`: p95 <= 2000 ms;
- `L_RISK_FIREWALL`: p95 <= 100 ms, p99 <= 250 ms;
- `L_OMS_DISPATCH`: p95 <= 100 ms;
- `L_UI`: p95 <= 2000 ms.

A single explicit miss is WARNING. Three explicit consecutive miss windows require architecture review. These are reference architecture objectives, not production SLA certification.

## Capacity lineage

P22-I consumes the canonical P02 envelopes:

- OPERATING: average 2,000 eps; peak 20,000 eps; 75 streams; 10 concurrent agent runs;
- STRESS: average 10,000 eps; peak 50,000 eps; 200 streams; 25 concurrent agent runs.

At 70% of an OPERATING limit, capacity pressure is surfaced for review. Reaching a STRESS boundary requires architecture review. No automatic scaling occurs.

## Cost guardrails

No absolute monthly budget is stored in policy. Budget evaluation requires an explicit caller-supplied Owner budget.

Canonical guardrails from the architecture envelope:

- 70% projected monthly budget: alert and review forecast;
- 85%: recommend throttling discretionary research;
- 100%: recommend freezing discretionary new research spend;
- 2x daily-cost anomaly: investigate and recommend circuit-breaking optional AI/research workloads.

Recommendations never apply to Risk, Firewall, Security, Audit, Reconciliation or Kill Switch workloads.

## Authority boundary

P22-I is monitoring only. It does not automatically scale infrastructure, shed workloads, throttle safety-critical components, mutate runtime state, access credentials/network, mutate external orders, or certify production SLA performance.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

P22-J — Operations Validation Gate remains NOT_STARTED until P22-I is canonically closed.

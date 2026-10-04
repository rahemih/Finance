# NEXUS QUANT — Capacity / Cost Envelope

STATE = P02-H BASELINE  
TASK = `FIN-P02-WH-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Define provisional architecture envelopes for throughput, storage, latency, research/agent workload, observability, recovery and cost.

These values are **design assumptions**, not production measurements.

P05/P06/P17/P18/P22 must replace them with measured evidence.

NEXUS QUANT is not designed as an HFT system.

## 2. Workload scenarios

### BOOTSTRAP

Provisional:
- ~25 active instrument/provider streams;
- average 500 events/s;
- peak 5,000 events/s;
- 10 concurrent user sessions;
- 5 concurrent agent runs.

Purpose:
initial engineering, Demo and contract validation.

### OPERATING

Provisional:
- ~75 active instrument/provider streams;
- average 2,000 events/s;
- peak 20,000 events/s;
- 20 concurrent user sessions;
- 10 concurrent agent runs.

This is the primary design point for P04 technology selection.

### STRESS

Provisional:
- ~200 active streams;
- average 10,000 events/s;
- peak 50,000 events/s;
- 50 user sessions;
- 25 concurrent agent runs.

This is a review boundary, not an expected normal workload.

Exceeding it requires architecture review.

## 3. Storage-growth arithmetic

Formula:

`GB/day = events_per_sec × event_bytes × 86400 / 1e9`

Wolfram-checked examples:

| Scenario | Avg EPS | Event bytes | Raw GB/day | Raw TB/30d | 3:1 GB/day | 5:1 GB/day |
|---|---:|---:|---:|---:|---:|---:|
| BOOTSTRAP | 500 | 500 | 21.6 | 0.648 | 7.2 | 4.32 |
| BOOTSTRAP | 500 | 1000 | 43.2 | 1.296 | 14.4 | 8.64 |
| OPERATING | 2,000 | 500 | 86.4 | 2.592 | 28.8 | 17.28 |
| OPERATING | 2,000 | 1000 | 172.8 | 5.184 | 57.6 | 34.56 |
| STRESS | 10,000 | 500 | 432.0 | 12.96 | 144.0 | 86.4 |
| STRESS | 10,000 | 1000 | 864.0 | 25.92 | 288.0 | 172.8 |

Important:
- actual event size varies strongly by channel;
- order-book data can be materially larger;
- compression is codec/layout dependent;
- raw retention is provider-right dependent;
- these are not procurement numbers.

## 4. Retention tiers

### HOT
Provisional 7 days.

Use:
- recent canonical events;
- selected raw evidence where licensed;
- short replay/investigation windows.

### WARM
Provisional 30–90 days.

Use:
- canonical history;
- selected raw;
- quality/provenance;
- features.

### COLD
90 days to multi-year when permitted.

Use:
- compressed history;
- macro vintages;
- replay manifests;
- derived features;
- model artifacts;
- audit evidence.

Provider licensing can shorten or prohibit raw retention.

## 5. Backpressure / buffering

At least 60 seconds of OPERATING peak ingress should be absorbable through bounded buffering/backpressure without silent loss.

Example raw payload only:

`20,000 eps × 1,000 bytes × 60s = 1.2 GB`

STRESS example:

`50,000 eps × 1,000 bytes × 60s = 3.0 GB`

Actual implementation must include:
- framing;
- runtime objects;
- indexes;
- replication;
- metadata;
- disk spill where justified.

Payload-only math is not enough for provisioning.

## 6. Latency classes

### L_FAST_DATA

Adapter receive → canonical event.

Provisional:
- p95 <= 250 ms;
- p99 <= 1 s

under OPERATING.

Excludes upstream provider/source latency.

### L_SIGNAL_STANDARD

Quality-qualified evidence cutoff → SignalCandidate.

Provisional:
- p95 <= 2 s for fast/intraday pipelines.

Slower macro/research workflows declare their own horizon.

### L_RISK_FIREWALL

SignalCandidate/current state → FirewallVerdict.

Provisional internal target:
- p95 <= 100 ms;
- p99 <= 250 ms.

Critical timeout/unknown state fails closed.

### L_OMS_DISPATCH

ApprovedTradeIntent → provider-adapter dispatch start.

Provisional internal target:
- p95 <= 100 ms.

Broker/network acknowledgement is excluded.

### L_UI

Ordinary internal dashboards:
- p95 <= 2 s.

Long research jobs are explicit asynchronous workloads.

## 7. Agent / model envelope

Project baseline:
private owner/team <=10.

Concurrent agent runs:
- BOOTSTRAP: 5
- OPERATING: 10
- STRESS: 25

Every run requires:
- max turns;
- max tool calls;
- max wall-clock;
- token budget;
- cost budget;
- retry limit.

Cost pressure may slow/pause research Agents.

It must not disable:
- Risk;
- Firewall;
- Security;
- mandatory Audit;
- Reconciliation;
- Kill Switches.

## 8. Research compute classes

### RC_INTERACTIVE
Seconds to minutes.

Examples:
small replay, feature inspection, scenario analysis.

### RC_BATCH
Minutes to hours.

Examples:
multi-instrument backtest, walk-forward, feature rebuild.

Early default:
2–4 heavy concurrent jobs.

### RC_HEAVY
Hours.

Examples:
Monte Carlo, large parameter sweep, retraining.

Early default:
1–2 concurrent jobs.

Expansion requires measured cost/capacity evidence.

## 9. Observability overhead

Plan provisionally for 5–15% additional storage/ingest overhead for retained operational telemetry, excluding extremely verbose debug traces.

Mandatory:
- execution;
- risk;
- security;
- audit

evidence must not be sampled away.

High-volume low-risk debug telemetry may be sampled.

## 10. Provisional DR targets

### DR0 — Execution Authority

Provisional objectives:
- local persisted RPO <= 1 minute;
- SAFE_MODE recovery <= 15 minutes;
- NORMAL <= 60 minutes after successful reconciliation.

External broker truth still requires reconciliation.

### DR1 — Control / Security

- RPO <= 15 minutes;
- RTO <= 4 hours.

### DR2 — Market / Historical / Research

- RPO <= 24 hours for rebuildable/backfillable data;
- RTO <= 24 hours.

Non-recoverable provider data may require tighter policy.

### DR3 — Rebuildable derived state

- RPO: N/A when fully reproducible;
- RTO <= 48 hours.

P22 must validate these by restore drills.

## 11. Cost equation

`monthly_total = market_data_fixed + exchange/index_entitlements + provider_usage + execution_fees + compute + storage + egress + model_ai + observability + backup_dr + security + support`

Pricing comes from current official evidence such as P01-E or later procurement tasks.

Architecture does not freeze vendor prices.

Owner absolute monthly budget is not yet set.

Current mode:
`BALANCED_NON_BINDING_DEFAULT`

## 12. Budget guardrails

At 70% projected monthly budget:
- alert;
- review forecast.

At 85%:
- defer/throttle noncritical research;
- reduce optional model diversity;
- defer heavy experiments.

At 100%:
- freeze discretionary new research spend.

A sudden 2× daily cost anomaly:
- circuit-break optional AI/research workloads;
- investigate.

Cost controls never disable core safety/security/audit/reconciliation.

## 13. Architecture review triggers

Review required when:
- sustained ingestion repeatedly consumes >70% of OPERATING envelope;
- workload approaches/exceeds STRESS;
- average rate >10,000 eps;
- peak >50,000 eps;
- active streams >200;
- agent concurrency >25;
- storage growth deviates >50% from forecast for 7 days;
- critical latency SLO fails across three measurement windows.

Do not silently assume horizontal scale solves an architectural mismatch.

## 14. Downstream measurement obligations

### P04
Benchmark:
- runtime;
- database;
- queue/stream;
- storage;
- serialization;
- telemetry overhead.

### P05
Measure:
- real event sizes;
- sustained/peak rates;
- burst/backpressure;
- p50/p95/p99 ingestion latency.

### P06
Measure:
- compression;
- partition size;
- retention/compaction;
- replay scan rate;
- feature rebuild time.

### P17/P18
Measure:
- backtest/retraining compute;
- model/token cost;
- queue saturation.

### P22
Measure:
- backup duration;
- restore throughput;
- real RPO/RTO.

## 15. Safety

All numbers remain provisional until benchmarked.  
No cloud/vendor plan selected.  
No purchase/provisioning performed.  
CANARY = DISABLED  
LIVE = DISABLED  
AUTO_TRADING = DISABLED

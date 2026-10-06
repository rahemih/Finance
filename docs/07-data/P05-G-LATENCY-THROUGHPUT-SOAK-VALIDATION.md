# P05-G — Latency / Throughput / Soak Validation

Task: `FIN-P05-WG-001`  
Linear: `HOS-193`  
State: IN_PROGRESS  
Lead: A2 Data Agent  
Supporting: A9 Operations, A10 Evidence/Audit, A1 Architecture, A8 Security, A0 Governance

## Objective

Replace the provisional P02-H real-time-data performance assumptions with measured CI evidence for the currently implemented offline engineering pipeline.

This is not a commercial provider SLA test and not an Internet/network latency claim.

## Canonical design point

P02-H defines:

- OPERATING average: 2,000 events/s;
- OPERATING peak: 20,000 events/s;
- STRESS review boundary: 50,000 events/s;
- L_FAST_DATA: p95 <= 250 ms and p99 <= 1,000 ms under OPERATING;
- upstream provider/source latency excluded.

P05-G does not weaken these thresholds.

## Measurement boundary

Measured latency path:

`decoded provider message mapping -> adapter contract -> canonical normalization -> canonical event availability`

The current P05 baseline does not implement production transport, so these measurements exclude:
- provider-side publication latency;
- Internet/network distance;
- production socket/WebSocket scheduling;
- commercial provider entitlement/SLA behavior.

Those exclusions are explicit evidence, not hidden omissions.

## Certifications

P05-G requires:

1. **L_FAST_DATA latency** — p95 <= 250 ms and p99 <= 1,000 ms.
2. **Canonical stream throughput** — >= 20,000 accepted events/s.
3. **OPERATING peak burst** — exactly 20,000 events accepted and drained with zero rejection.
4. **Soak-equivalent workload** — at least 120,000 events, equal to 60 seconds of the 2,000 events/s OPERATING average, with zero rejection and measured throughput >= 2,000 events/s.
5. **STRESS boundary** — 50,000 events/s is reported only. P05-G does not silently promote STRESS to an OPERATING promise.

## Evidence model

Timing evidence is inherently non-deterministic and therefore must **not** be byte-compared between runs.

P05-G separates:
- deterministic policy/contract/safety evidence, which is generated twice and byte-compared;
- measured performance evidence, which is generated once per Governance run and retained as an artifact.

This prevents false claims of deterministic timing.

## Safety

- network required: NO;
- credentials required: NO;
- production endpoint: NONE;
- automatic data failover: DISABLED;
- CANARY: DISABLED;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED.

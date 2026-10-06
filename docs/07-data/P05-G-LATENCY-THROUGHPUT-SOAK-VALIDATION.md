# P05-G — Latency / Throughput / Soak Validation

Task: `FIN-P05-WG-001`  
Linear: `HOS-193`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- implementation PR: `#130` = MERGED;
- implementation head: `01740217b4464f25f6143b97bff7d5eaaff093ab`;
- implementation merge SHA: `d649a649a4c1a0a4af7828e138e1a3d3a47ab215`;
- PR Governance run: `37459307993` = SUCCESS;
- PR artifact: `11411103044`;
- PR artifact digest: `sha256:a437a00347d49fef0c11ff64a123de8d3ee443c06401a51ecd6074e15b5fc5ff`;
- post-merge Governance run: `37459469108` = SUCCESS;
- post-merge artifact: `11411003641`;
- post-merge artifact digest: `sha256:eeca4ac81f26ee3dfa408ba224ebab4f862b5fb06ba2ac758214026fcc69eff2`;
- post-merge Branch Hygiene run: `37459469136` = SUCCESS;
- strict Pyright: `0 errors / 0 warnings`;
- foundation tests: `22/22 PASS`;
- P05 tests: `100/100 PASS`;
- measured post-merge p95: `0.043505 ms`;
- measured post-merge p99: `0.053039 ms`;
- measured canonical stream throughput: `403228.83 events/s`;
- measured soak-equivalent throughput: `421840.98 events/s`;
- deterministic contract evidence SHA-256: `678a290279ce9cb9af3f2c753a2bf3a3c3944fda5521fbf492bcc6b05e339167`;
- measured evidence SHA-256: `74b3fab6693e551f5a60ee0811fd85e05c98f54eaa94de3978b677caa57b943d`;
- reproducible artifact SHA-256: `30627334f87438e95dc4317548f7a18f979f489755833b4a209412d37baed1e5`;
- rollback manifest SHA-256: `3433ced364ef0ed8b55fcb5ff1fce183c9436f62b22b76082c7c2207464deb2c`;
- verdict: PASS.

Next ready workstream: `P05-H — Real-Time Data Gate Closure`.

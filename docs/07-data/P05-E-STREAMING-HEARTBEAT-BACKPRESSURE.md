# P05-E — Streaming / Heartbeat / Backpressure

Task: `FIN-P05-WE-001`  
Linear: `HOS-191`  
State: IN_PROGRESS  
Lead: A2 Data Agent  
Supporting: A1 Architecture, A8 Security, A9 Operations, A10 Evidence/Audit, A0 Governance

## Objective

Establish the first provider-neutral canonical streaming boundary after P05-D normalization. This workstream is intentionally offline and in-process: it defines deterministic buffering, liveness and backpressure semantics without selecting an external broker, opening provider connections or granting execution authority.

## Architecture binding

P02-C requires bounded ingress buffering, session/sequence metadata preservation and provider-neutral canonical event flow. P02-H requires at least 60 seconds of the OPERATING peak ingress envelope to be absorbable through bounded buffering/backpressure without silent loss.

The provisional OPERATING peak is 20,000 events/second. P05-E therefore configures a non-preallocated bound of 1,200,000 canonical events:

`20,000 events/s × 60 s = 1,200,000 events`

This is a semantic capacity baseline, not a P05-G performance certification.

## Canonical policy

- ordering: FIFO;
- overflow: explicit reject via `BackpressureError`;
- silent drop: forbidden;
- implicit overwrite: forbidden;
- high watermark: 840,000 events (70%);
- critical watermark: 1,080,000 events (90%);
- full: 1,200,000 events;
- heartbeat clock: canonical local receive time;
- provisional heartbeat timeout: 30 seconds;
- preallocation: disabled;
- disk spill: deferred;
- reconnect/failover/gap recovery: P05-F;
- throughput/latency/soak certification: P05-G.

## Heartbeat semantics

Liveness is evaluated per `provider + canonical_id` stream identity using the last accepted canonical local receive timestamp.

States:

- `NEVER_SEEN`: no accepted event exists for the stream;
- `HEALTHY`: observation is within the configured heartbeat timeout;
- `STALE`: observation exceeds the timeout.

The stream bus rejects a per-stream local receive timestamp regression and rejects a heartbeat observation earlier than the last accepted event. It never invents source timestamps.

## Backpressure semantics

Pressure is derived only from current bounded queue depth:

- `NORMAL`: below high watermark;
- `HIGH`: at/above high watermark and below critical;
- `CRITICAL`: at/above critical and below max;
- `FULL`: at max capacity.

A publish attempted while FULL fails loudly. Accepted queue contents remain intact and ordered.

## Evidence

Canonical CI runs:

1. all P05 unit tests;
2. deterministic P05-E evidence twice;
3. byte comparison of both evidence files;
4. SHA-256 of canonical evidence;
5. existing Pyright, SBOM, Trivy, reproducible-build and governance gates.

## Safety

- provider network connection: NONE;
- live credentials: NONE;
- external stream broker: NOT_SELECTED;
- trading authority: NONE;
- CANARY: DISABLED;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED.

# P06-H — Retention / Compaction / Storage-Cost Tests

Task: `FIN-P06-WH-001`  
Linear: `HOS-202`  
State: CANONICAL_COMPLETE  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Close the P06 measurement obligations with rights-aware retention checks, exact storage/partition arithmetic, compaction measurement, growth-deviation detection, replay-scan/feature-rebuild reference measurements and a cost model that never invents production prices.

## Rights-aware retention

Raw retention uses the P06-A rights states:

- `RETENTION_ALLOWED`;
- `RETENTION_ALLOWED_WITH_LIMIT`;
- `RETENTION_FORBIDDEN`;
- `RETENTION_UNVERIFIED`.

Forbidden and unverified raw retention fail closed.

Limited retention requires an explicit maximum and requested retention may not exceed it.

This workstream produces a plan only. It does not delete, expire, compact or rewrite production data.

## Capacity arithmetic

P06-H reproduces the P02-H equation exactly:

`raw bytes/day = events_per_sec × event_bytes × 86400`

It derives:

- raw GB/day;
- compressed GB/day from an explicit ratio;
- raw TB over requested retention;
- retained compressed GB;
- compressed partition size.

The canonical P02-H BOOTSTRAP, OPERATING and STRESS examples are unit-tested exactly.

## Compaction

Compaction ratio is measured from explicit byte counts:

`compression_ratio = input_bytes / output_bytes`

The P02-H 3:1 and 5:1 values remain planning reference points, not production guarantees. Synthetic certification checks arithmetic against those references; production storage measurements remain vendor/deployment dependent.

## Growth review trigger

The P02-H architecture-review trigger is preserved:

- deviation equal to 50%: report, no automatic architecture-review flag;
- deviation greater than 50%: architecture review required.

## Cost model

Production storage/scan/egress rates are intentionally absent.

Without an authoritative rate set, the cost result is:

`UNRESOLVED_RATE_REQUIRED`

Unit tests use synthetic `TEST_COST_UNITS` only to prove formula correctness. They are explicitly not vendor prices.

A later procurement/production task must inject current official rates with provenance before any production monetary estimate is authoritative.

## Measured CI reference benchmark

CI measures two synthetic reference paths:

1. sequential replay scan with checksum verification;
2. deterministic P06-F feature materialization rebuild.

These are CI sanity measurements, not production SLO claims. Floors are deliberately conservative and only detect severe regressions or broken paths.

## Retention tiers

P02-H provisional tiers remain:

- HOT: 7 days;
- WARM: 30–90 days;
- COLD: 90 days to multi-year where rights permit.

Provider/dataset rights always override provisional architecture retention assumptions.

## P06 closure boundary

P06-H is the final P06 workstream.

Canonical closure result:

- P06 = CANONICAL_COMPLETE;
- P07 = NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED;
- no named post-P06 gate is claimed because none is defined by the frozen canonical evidence reviewed for this closure.

## Closure evidence

- Implementation PR: `#149` = MERGED
- Final implementation head: `26ae0426fa1b264e0ce8a097884a6c5fbb0a0877`
- Implementation merge SHA: `8f375b7b617589ec3786f2a45208182e138c826b`
- PR Governance: `37529299317` = SUCCESS
- PR artifact digest: `sha256:ca0655e9fb0ff2857a1151ac68d3cf556524ccba64a7fa3deb9a530a2b6ff3e9`
- Post-merge Governance: `37529493611` = SUCCESS
- Post-merge artifact digest: `sha256:f3eac59a29f6f8cafe6f2b10a572982548a4dcba49fb433266b40899ac8e770e`
- Post-merge Branch Hygiene: `37529493711` = SUCCESS
- Lock: RELEASED

## Safety

Production storage vendor: NOT_SELECTED.  
Production cost rates: UNRESOLVED_RATE_REQUIRED.  
Production mutation: false.  
Network required: false.  
Credentials required: false.  
Country assumption: NONE.  
CANARY: DISABLED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

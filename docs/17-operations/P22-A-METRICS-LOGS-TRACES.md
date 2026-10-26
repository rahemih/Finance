# P22-A — Metrics / Logs / Traces

Task: `FIN-P22-WA-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

## Objective

Establish a deterministic, vendor-neutral reference observability contract for NEXUS QUANT before health-state automation, diagnostics, self-healing or disaster-recovery work starts.

## Canonical contract

P22-A defines three content-addressed record types:

- MetricRecord — finite numeric values in the `nexus_quant.` namespace.
- LogRecord — structured severity, message, correlation and optional trace/span linkage.
- TraceRecord — explicit trace/span lineage with non-negative epoch-ns timing and monotonic start/end time.

All records are deterministic: identical inputs and policy produce identical record IDs.

## Bounded-cardinality policy

Telemetry attributes are allowlisted. Arbitrary identifiers such as user IDs, order IDs, raw account IDs or free-form tag names are not accepted. This prevents silent unbounded label cardinality from becoming part of the canonical contract.

Allowed dimensions are intentionally small: component, phase, workstream, operation, market, instrument_class, outcome and reason_code.

## Secret boundary

Secret-bearing attribute keys and common credential fragments in messages fail closed. P22-A is not a secret-redaction service and must not be treated as permission to log secrets.

## Authority boundary

P22-A is reference-only:

- no network collector;
- no vendor exporter;
- no credentials;
- no system-state mutation;
- no automated diagnostics;
- no self-healing;
- no risk-policy relaxation;
- no external-order authority;
- no Live execution authority.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled.

## Dependency and next step

P21 is CANONICAL_COMPLETE and P22 Owner authorization is consumed. P22-B remains NOT_STARTED until P22-A is canonically closed.

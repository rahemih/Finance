# ADR-0008 — Logical Data Layers, Replay & Lineage

Status: ACCEPTED  
Task: `FIN-P02-WC-001`

## Context

NEXUS QUANT must support real-time operation, historical research, backtesting, decision replay, audit, learning and recovery while preserving provider rights and avoiding look-ahead leakage.

A single mutable database or "latest state" model cannot satisfy those requirements safely.

## Decision

Adopt the logical data-layer model defined in:

- `docs/04-architecture/DATA-FLOW-STORAGE-ARCHITECTURE.md`
- `docs/04-architecture/data-flow-storage-architecture.json`

The architecture separates:

1. edge capture;
2. raw evidence;
3. canonical events;
4. quality/provenance;
5. operational projections;
6. feature/evidence;
7. research/replay manifests;
8. model/experiment artifacts;
9. audit/evidence.

Observed truth is append-only/versioned where contractual rights permit.

Corrections and revisions append new versions/events rather than silently rewriting history.

Operational mutable state is a rebuildable projection, not the sole historical truth.

Replay requires explicit manifests containing exact dataset/schema/config/code/model versions and integrity references.

Provider licensing/retention constraints are attached to datasets and can restrict or expire raw content without erasing non-content audit facts.

## Alternatives considered

### One mutable operational database as system of record
Rejected because it cannot reliably reconstruct what the system knew at historical decision time.

### Latest-value macro/history model
Rejected because revisions would create look-ahead bias.

### Raw-data retention assumed indefinitely
Rejected because provider/exchange licensing can prohibit or limit retention.

### Physical technology selection in P02-C
Rejected because logical requirements must remain portable and P04 owns concrete engineering choices.

## Consequences

Positive:
- deterministic replay;
- better anti-lookahead guarantees;
- clear provenance and lineage;
- recoverable operational projections;
- provider portability;
- licensing-aware storage.

Negative:
- more metadata/versioning;
- increased storage/manifest complexity;
- retention policy must be dataset-specific.

## Risks / mitigations

Risk: lineage metadata becomes inconsistent.  
Mitigation: mandatory manifest/version IDs and schema validation.

Risk: raw retention rights conflict with audit needs.  
Mitigation: preserve non-content audit references and permitted derived metadata while enforcing content deletion/expiry.

Risk: replay accidentally uses future revisions.  
Mitigation: enforce observed_at/release-time cutoff against simulation clock.

Risk: operational state cannot be rebuilt in practical time.  
Mitigation: allow periodic snapshots/checkpoints while preserving authoritative event history.

## Validation / evidence

P02-H must quantify storage/event-rate assumptions.

P04/P06 must choose technologies that satisfy:
- immutable/versioned evidence;
- replay manifests;
- recoverable projections;
- integrity checks;
- rights-aware retention.

P07 validates quality/provenance behavior.

P19 validates decision replay/digital twin.

## Rollback / supersession

Concrete storage mechanisms may change without superseding this ADR if the logical guarantees remain intact.

Any change that removes replayability, lineage, revision history or licensing-aware retention requires explicit ADR supersession and A1/A2/A8/A10 review.

## Related tasks / gates

P02-C, P02-H, P04, P05, P06, P07, P17, P19, P22, G2.

# P18-B — Decision / Outcome Journal

State: IN_PROGRESS  
Task: `FIN-P18-WB-001`  
Phase: P18 — Continuous Demo Learning

## Objective

Create an immutable, point-in-time-safe journal of Demo/Paper decisions and their later-observed outcomes. The journal is the auditable learning memory between P18-A execution and P18-C dataset curation.

## Decision record

Every decision record preserves:

- P18-A session specification and state identities;
- canonical decision ID, sequence and decision time;
- asset and requested quantity delta;
- Strategy Registry ID/version;
- Model Registry ID/version;
- signal ID;
- independent risk-decision ID;
- pre-trade firewall-decision ID;
- market-evidence SHA-256 known at decision time.

Records are content-addressed and append-only.

## Outcome record

Every outcome record references the exact decision-record SHA-256 and carries:

- outcome ID;
- observation time;
- explicit outcome-definition ID and version;
- deterministic numeric outcome value;
- outcome evidence SHA-256.

An outcome cannot exist for an unknown decision and cannot be observed before the decision time.

## Point-in-time safety

`view_at(as_of_ns)` exposes only:

1. decisions whose decision time is not later than `as_of_ns`;
2. outcomes whose `observed_at_ns` is not later than `as_of_ns`;
3. outcomes whose referenced decision is visible in the same view.

This prevents future outcome labels from leaking into historical learning views.

## Authority boundary

P18-B does not curate a training dataset, transform labels for training, run experiments, retrain models or authorize promotion. Those responsibilities remain with P18-C and later workstreams.

It has no broker/exchange routing, Live Trading, Auto Trading or automatic live-promotion authority.

## Validation

The governed tests and deterministic CI evidence cover content-addressed identity, journal-root determinism, duplicate/conflict rejection, unknown-decision rejection, temporal outcome safety, exact lineage preservation and future-outcome exclusion.

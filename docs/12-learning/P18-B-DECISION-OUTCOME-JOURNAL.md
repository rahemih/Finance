# P18-B — Decision / Outcome Journal

State: CANONICAL_COMPLETE  
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


## Canonical closure

Implementation PR #363 is MERGED.

- implementation head: `6c311d59eb6ab7880d677c9763488ae63c323ab8`;
- Governance: `39017065770` / SUCCESS;
- deterministic foundation artifact: `sha256:3491ad0457bf91ffaafccf2b3b20dd9436410574e316b7928b3764a6178e3576`;
- implementation merge SHA: `c1dd0ae29fca2c01246fc8214b7e005703d31621`;
- governed lock: RELEASED;
- P18-C: READY_NOT_STARTED;
- P19: NOT_STARTED.

P18-B closure does not create dataset/training, retraining, promotion, execution or live-trading authority.

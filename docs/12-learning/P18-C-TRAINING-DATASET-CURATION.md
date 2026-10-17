# P18-C — Training Dataset Curation

State: IN_PROGRESS  
Task: `FIN-P18-WC-001`  
Phase: P18 — Continuous Demo Learning

## Objective

Curate immutable, reproducible, point-in-time-safe training datasets from the canonical P18-B Decision / Outcome Journal without starting experiments or model training.

## Dataset specification

Every curated dataset binds:

- source P18-B journal-root SHA-256;
- one outcome-definition ID and version;
- an explicit final dataset cutoff;
- deterministic temporal boundaries for TRAIN, VALIDATION and TEST.

The dataset specification itself is content-addressed.

## Row lineage

Every curated row preserves the exact:

- decision-record and outcome-record identities;
- decision ID/time and outcome observation time;
- asset and requested quantity;
- Strategy Registry identity/version;
- Model Registry identity/version;
- signal ID;
- risk-decision ID;
- firewall-decision ID;
- decision-time market evidence;
- outcome definition/version, value and evidence.

Rows are content-addressed independently from the dataset manifest.

## Point-in-time and split leakage controls

A record is never eligible merely because its outcome is known by the final dataset cutoff.

For TRAIN, its label must have been observable by `train_end_ns`.  
For VALIDATION, its label must have been observable by `validation_end_ns`.  
For TEST, its label must have been observable by the final `dataset_cutoff_ns`.

This prevents later-known labels from leaking backwards into earlier temporal partitions.

The curation engine deterministically excludes:

- decisions after the final dataset cutoff;
- missing outcomes;
- outcomes after the final cutoff;
- outcomes whose label was not observable by the cutoff of their assigned split.

Unknown decision references, duplicate/conflicting identities, multiple labels for one decision, outcome-definition mismatch and outcome-before-decision violations fail closed.

## Immutable manifest

The dataset manifest contains:

- dataset-spec identity;
- all row identities;
- row identities by TRAIN / VALIDATION / TEST;
- deterministic exclusion records and reasons;
- explicit authority-boundary markers.

The manifest is content-addressed as `dataset_id`.

## Authority boundary

P18-C curates data only. It does not run an experiment, train/retrain a model, choose a Champion/Challenger or authorize promotion. P18-D owns Experiment Tracking.

There is no broker/exchange routing, automatic live promotion, Live Trading or Auto Trading authority.

## Validation

Governed tests and deterministic CI evidence cover temporal split assignment, split-specific label availability, final cutoff handling, lineage preservation, identity/deduplication invariants, outcome-definition uniformity and authority boundaries.

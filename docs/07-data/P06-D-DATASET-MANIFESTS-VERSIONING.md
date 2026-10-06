# P06-D — Dataset Manifests & Versioning

Task: `FIN-P06-WD-001`  
Linear: `HOS-198`  
State: CANONICAL_COMPLETE  
Implementation PR: `#141` / MERGED  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Create immutable, reproducible dataset identities over canonical P06 historical records so research, replay, backtesting and later model artifacts can refer to an exact dataset version rather than an informal query.

## Version contract

A dataset version is SHA-256 over a canonical manifest body containing:

- dataset name and schema version;
- half-open dataset time window;
- rights class;
- exact P06-C query-index fingerprint;
- canonical member count;
- membership root;
- canonical ordered member list.

Input ordering does not change the version. Any material record-content or lineage change does.

## Member integrity

Each member records:

- record ID;
- canonical instrument ID;
- event time;
- digest of the canonical P06-C record content;
- exact P06-A raw payload SHA-256;
- safe relative raw-object reference.

Each member has its own deterministic digest. The dataset membership root is SHA-256 over the ordered member digests.

## Immutable reference store

The reference implementation writes:

`manifests/<dataset_name>/<dataset_version>.json`

The version is content-addressed. Rewriting identical bytes is idempotent. Existing bytes that differ for the same version fail closed. Loading revalidates member digests, membership root and dataset version.

This filesystem implementation is an offline contract reference, not a production storage selection.

## Downstream boundary

P06-E owns macro vintage semantics.  
P06-F owns feature definitions/materialization.  
P06-G owns replay snapshot interfaces.  
P06-H owns retention/compaction/storage-cost certification.

P06-D provides the immutable dataset reference these later workstreams can consume.

## Vendor and safety boundary

Production manifest storage vendor: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
CANARY: DISABLED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

P06-D closure is canonical. P06-E is READY_NOT_STARTED under the existing P06 Owner authorization.

## Closure evidence

- Implementation PR: `#141` = MERGED
- Final implementation head: `ab32444222dac7fedec7117ee16bb225d0fa1ec0`
- Implementation merge SHA: `8ca5faf7c82a86a47784fe7748c731fd67f78719`
- PR Governance: `37482853727` = SUCCESS
- PR artifact digest: `sha256:5d6fc6470729890099bd6ff123fb3c3f1aa0d4f656cecd047b0fef444644b7a1`
- Post-merge Governance: `37483116686` = SUCCESS
- Post-merge artifact digest: `sha256:1a79010d0cc32a8020085cbff52beec3606248bae9d791b20187e8a226355250`
- Post-merge Branch Hygiene: `37483116634` = SUCCESS
- Lock: RELEASED

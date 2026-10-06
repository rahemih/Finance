# P06-D — Dataset Manifests & Versioning

Task: `FIN-P06-WD-001`  
Linear: `HOS-198`  
State: IN_PROGRESS  
Implementation PR: `#141` / OPEN  
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

P06-E remains blocked until P06-D canonical closure.

# P06-C — Time-Series Optimized Query Layer

Task: `FIN-P06-WC-001`  
Linear: `HOS-197`  
State: CANONICAL_COMPLETE  
Implementation PR: `#139` / MERGED  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Provide a deterministic, vendor-neutral reference query layer for governed canonical historical records while retaining raw-evidence linkage and avoiding premature selection of a production database.

## Query model

The reference index uses:

- canonical instrument ID + fixed time partition as the primary logical partition;
- stable event-time ordering inside each partition;
- binary-search slicing for half-open time windows;
- optional provider and event-kind filters;
- bounded result limits and bounded partitions per query;
- deterministic tie-breaking by event time, canonical ID, sequence ID and record ID.

The implementation is intentionally in-memory and offline. It proves the contract and access pattern, not a production database choice.

## Record lineage

Each record preserves:

- unique record ID;
- canonical instrument ID;
- canonical event kind/provider;
- event and receive times;
- provider sequence ID;
- canonical schema version;
- canonical payload JSON;
- exact source payload SHA-256;
- safe relative P06-A raw archive object reference;
- provenance metadata.

P06-D owns dataset manifests/versioning. P06-C does not claim that the query-index fingerprint is a dataset-version identifier.

## Optimization evidence

A bounded query only visits existing partitions for the requested canonical IDs and uses binary search to slice records by event time before secondary filters. CI proves candidate pruning on deterministic fixtures.

A separate synthetic benchmark measures 20,000 records and 400 bounded queries. The benchmark is a CI regression guard, not production capacity evidence.

## Vendor boundary

Production query/storage vendor: NOT_SELECTED.

No PostgreSQL, TimescaleDB, ClickHouse, cloud object store, managed database or provider SDK is selected or imported by this workstream. Concrete production selection requires later governed evidence and must remain compatible with the frozen P02 storage architecture.

## Safety

Network required: false  
Credentials required: false  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

P06-C closure is canonical. P06-D is READY_NOT_STARTED under the existing P06 Owner authorization.

## Closure evidence

- Implementation PR: `#139` = MERGED
- Final implementation head: `78c41e5849c11a9493b5c839ac4d5a4f0d6bedbd`
- Implementation merge SHA: `b430a8a1cf2cae11c05c4796dff28b472fb196e3`
- PR Governance: `37479773448` = SUCCESS
- PR artifact digest: `sha256:479a70595cd1363118ed36374f88f6d0444a22dcb75f8512617c89304d5226eb`
- Post-merge Governance: `37480045004` = SUCCESS
- Post-merge artifact digest: `sha256:166b40d458d5fbfabd517b1798e6875df6e7bc16ce0a3eb7735a05da6d61755d`
- Post-merge Branch Hygiene: `37480044940` = SUCCESS
- Lock: RELEASED

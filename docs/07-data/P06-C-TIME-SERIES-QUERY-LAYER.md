# P06-C — Time-Series Optimized Query Layer

Task: `FIN-P06-WC-001`  
Linear: `HOS-197`  
State: IN_PROGRESS  
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

P06-D remains blocked until P06-C canonical closure.

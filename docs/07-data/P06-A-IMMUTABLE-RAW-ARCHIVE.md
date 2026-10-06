# P06-A — Immutable Raw Archive

Task: `FIN-P06-WA-001`  
Linear: `HOS-195`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Establish a source-faithful immutable raw-evidence archive contract for later backfill, dataset versioning and deterministic replay without prematurely selecting a production storage vendor.

## Architecture boundary

P02 assigns D04 Raw / Historical Data to A2 and requires immutable/versioned source-faithful evidence, provider/source metadata, checksum/hash integrity, rights/retention classification and replayable historical truth distinct from mutable operational projections.

## Raw evidence contract

Every object records exact raw bytes, SHA-256, provider, source stream, nanosecond capture time, optional source event/time, media type, rights state, retention class and optional expiry. Object keys are content-addressed; the stream identity is hashed for portable paths.

## Rights / retention

- RETENTION_ALLOWED → permitted.
- RETENTION_ALLOWED_WITH_LIMIT → requires explicit expiry.
- RETENTION_FORBIDDEN → fail closed.
- RETENTION_UNVERIFIED → fail closed.

This baseline does not claim any provider contract permits raw retention.

## Immutability

Overwrite is forbidden. Identical payload+metadata is idempotent. Partial pairs, tampered objects and metadata conflicts fail closed. P06-H owns later lifecycle deletion/compaction/storage-cost validation.

## Reference implementation

`FilesystemRawArchive` is deterministic and offline for CI. It is not a production object-store selection.

Production storage vendor: `NOT_SELECTED`.

## Validation

Strict Pyright, exact-byte preservation, SHA-256 integrity, deterministic metadata, rights gates, limited-retention expiry, idempotency, tamper/partial-pair rejection, provider-neutral core and deterministic evidence generated twice.

## Safety

Network: NONE  
Credentials: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

P06-B remains blocked until P06-A canonical closure.

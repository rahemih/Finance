# P06-A — Immutable Raw Archive

Task: `FIN-P06-WA-001`  
Linear: `HOS-195`  
State: CANONICAL_COMPLETE  
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

P06-A closure is canonical. P06-B is READY_NOT_STARTED under the existing P06 Owner authorization.

## Closure evidence

- Implementation PR: `#135` = MERGED
- Final implementation head: `b79b44c0bf32b5077ce1bda0518a1555e82d10c3`
- Merge SHA: `d9080cf3a9ec6a2456c7697cc0029feebb2976d0`
- PR Governance: `37467639427` = SUCCESS
- PR artifact digest: `sha256:3bdbeb2bb6dff77eb9a7bca06ed0ce0b1ddaf04abede55e82c674646b57c0a0b`
- Post-merge Governance: `37467800764` = SUCCESS
- Post-merge artifact digest: `sha256:72d1b4252fa9ac3d8bf2de43070bfd5edd8584ee5e7d3806f787ed3eedd430c7`
- Post-merge Branch Hygiene: `37467800591` = SUCCESS
- Lock: RELEASED


# P06-B — Historical Backfill

Task: `FIN-P06-WB-001`  
Linear: `HOS-196`  
State: CANONICAL_COMPLETE  
Lead: A2 Data  
Supporting: A0 Governance, A1 Architecture, A4 Quant, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Build the governed historical-backfill baseline on top of the canonical P06-A immutable raw archive without assuming real provider credentials, entitlements, network connectivity or a production storage vendor.

## Reference execution model

The P06-B implementation accepts an already-acquired sequence of historical provider payload pages and:

1. validates a half-open historical window;
2. validates non-empty contiguous page ordinals before any archive mutation;
3. enforces configured page-count and total-byte bounds;
4. computes a deterministic request fingerprint from request metadata plus exact page digests;
5. archives every page through the P06-A content-addressed raw archive;
6. preserves exact provider payload bytes;
7. propagates rights/retention and provenance metadata;
8. makes identical reruns idempotent.

This is an offline reference execution contract. It does not fetch from a live provider.

## Rights and entitlement boundary

Historical retention authorization is inherited from P06-A and remains fail-closed:

- `RETENTION_ALLOWED` may archive.
- `RETENTION_ALLOWED_WITH_LIMIT` requires an explicit expiry.
- `RETENTION_FORBIDDEN` is rejected.
- `RETENTION_UNVERIFIED` is rejected.

Production historical provider entitlement is `NOT_ASSUMED`. No provider-specific acquisition adapter is created in this workstream.

## Determinism and replay compatibility

The request fingerprint covers:

- provider;
- source stream;
- historical window;
- rights/retention metadata;
- media type;
- ordered page ordinals;
- exact page SHA-256 and sizes;
- capture/source event/source timestamp metadata.

P06-D will own dataset manifests/versioning and P06-G will own replay snapshot interfaces. The P06-B fingerprint is a backfill-run identity, not a dataset-version contract.

## Failure behavior

The reference runner fails before mutation for:

- empty page input;
- non-contiguous or duplicate/out-of-order ordinals;
- invalid historical windows;
- page-count limit violations;
- total-byte limit violations.

Rights failures occur in the immutable raw archive before the first unauthorized payload is written.

## Safety

Production historical provider entitlement: NOT_ASSUMED  
Production storage vendor: NOT_SELECTED  
Network required: false  
Credentials required: false  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

P06-B closure is canonical. P06-C is READY_NOT_STARTED under the existing P06 Owner authorization.

## Closure evidence

- Implementation PR: `#137` = MERGED
- Final implementation head: `005f89cf0475708f396f49744f44e0e879117e26`
- Implementation merge SHA: `f9ba46b076fafd448fe8b5ed7edfbaaa30d83d95`
- PR Governance: `37476310712` = SUCCESS
- PR artifact digest: `sha256:65056f011afa75b8e3207c779ac841eee18cf57069695297a21c8aa9088b95fe`
- Post-merge Governance: `37476473700` = SUCCESS
- Post-merge artifact digest: `sha256:8f9cac3e5fcdcd58f3f7a0f007e7640582274b363892d3048aef97a9de688990`
- Post-merge Branch Hygiene: `37476473587` = SUCCESS
- Lock: RELEASED
- Canonical closure PR: `#138`

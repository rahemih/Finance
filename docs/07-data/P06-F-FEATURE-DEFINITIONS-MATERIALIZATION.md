# P06-F — Feature Definitions & Materialization

Task: `FIN-P06-WF-001`  
Linear: `HOS-200`  
State: IN_PROGRESS  
Lead: A4 Quant  
Supporting: A0 Governance, A1 Architecture, A2 Data, A3 Fundamental/Macro, A8 Security, A9 Operations, A10 Evidence/Audit

## Objective

Create reproducible feature artifacts whose definition, code/config identity, source data, macro vintages, quality eligibility and point-in-time cutoff are all explicit and verifiable.

## Feature definition identity

A feature definition is content-addressed from:

- feature name;
- definition version;
- output type;
- exact code SHA-256;
- exact config SHA-256;
- description.

Any semantic/code/config change creates a different definition ID.

## Materialization identity

Each materialization records:

- feature definition ID plus definition version;
- exact code/config SHA-256;
- entity/instrument ID;
- event time and as-of time;
- value;
- P06-D source dataset version;
- canonical sorted P06-E vintage IDs when applicable;
- source cutoff time;
- explicit quality status, quality policy version and quality evidence hash.

The materialization ID is SHA-256 over the canonical materialization body.

## Point-in-time rule

A feature may be materialized only when:

- `event_time <= as_of_time`;
- `source_cutoff <= as_of_time`;
- quality status is exactly `ELIGIBLE`.

This does not implement P07 quality scoring. P06-F consumes an explicit eligibility result and fails closed for INELIGIBLE, QUARANTINED or UNKNOWN.

## Deterministic batches

Feature batches canonicalize member order and compute a deterministic fingerprint from content-addressed materialization IDs. Duplicate logical keys fail closed.

## Reference artifact store

The offline reference store writes:

- `feature-definitions/<definition_id>.json`
- `feature-materializations/<definition_id>/<materialization_id>.json`

Identical rewrites are idempotent. Existing bytes that differ for the same content identity fail closed. Loads revalidate content identity.

This is not a production feature-store selection.

## Downstream boundary

P06-G owns replay snapshot interfaces and will consume exact feature materialization references.  
P06-H owns retention/compaction/storage-cost certification.  
P07 owns actual quality/provenance scoring and quarantine.

## Safety

Production feature storage vendor: NOT_SELECTED.  
Network required: false.  
Credentials required: false.  
Country assumption: NONE.  
CANARY: DISABLED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.

P06-G remains blocked until P06-F canonical closure.

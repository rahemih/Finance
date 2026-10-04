# NEXUS QUANT — Data Flow & Storage Architecture

STATE = P02-C BASELINE  
TASK = `FIN-P02-WC-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Define the logical flow, ownership, time semantics, storage classes, replayability and integrity requirements for NEXUS QUANT data before choosing concrete databases, object stores, stream brokers or cloud services.

This architecture is:
- provider-portable;
- country-neutral;
- replayable;
- licensing-aware;
- security-aware;
- technology-agnostic.

## 2. End-to-end flow

The canonical logical flow is:

`External Provider → Edge Capture → Raw Evidence → Canonical Events → Data Quality/Provenance → Feature/Evidence → Research/Replay → Model/Experiment → Audit/Evidence`

In parallel:

`Canonical/Quality/Domain Events → Operational Projections`

Operational projections are optimized for current operation. They are **not** the sole historical source of truth.

## 3. Time model

Every material market/economic event distinguishes:

- **source_time** — timestamp supplied by the original source/provider when available;
- **event_time** — canonical time represented by the event;
- **receive_time** — when NEXUS QUANT receives it;
- **process_time** — when a processing stage emits a derived artifact, when useful;
- **observed_at** — when a correction/revision/version first became known to the system.

Rules:
- receive time never silently replaces source time;
- late data keeps its original event time;
- revisions preserve the prior version;
- derived outputs record the exact data cutoff/watermark used.

## 4. Logical data layers

### L0 — Edge Capture
Owner: D02 Market Data Adapters

Purpose:
- bounded ingress buffering;
- provider session/sequence metadata;
- transport-level capture.

Not a long-term source of truth.

### L1 — Raw Evidence
Owner: D04 Raw / Historical Storage

Purpose:
- source-faithful immutable/versioned evidence;
- only where provider/data rights permit retention.

Requirements:
- provider identity;
- source metadata;
- checksum/hash;
- rights/retention class.

### L2 — Canonical Events
Owner: D03 Canonical Market Data

Purpose:
- provider-neutral normalized events.

Examples:
- trade;
- quote;
- book delta/snapshot;
- bar;
- macro event.

Every event preserves provenance and schema version.

### L3 — Quality & Provenance
Owner: D05 Data Quality & Provenance

Purpose:
- freshness;
- gaps;
- duplicates;
- outliers;
- cross-provider divergence;
- confidence;
- quarantine.

Critical unknown or quarantined data cannot silently flow as valid.

### L4 — Operational State
Owner: owning domain

Purpose:
- fast mutable current-state views.

Examples:
- current market snapshot;
- current position;
- current order state;
- current exposure;
- current system health.

Rule:
Operational state must be rebuildable from authoritative event/evidence history.

### L5 — Feature / Evidence
Owner: D06 Feature / Evidence

Purpose:
- versioned derived inputs for intelligence, quant and signal systems.

Must include:
- feature-definition version;
- code/config version;
- source dataset/snapshot reference;
- data-quality eligibility.

### L6 — Research / Replay Datasets
Owner: D04  
Consumers: D08, D13

Purpose:
- frozen manifests for backtests;
- deterministic replay;
- shadow/digital-twin analysis;
- experiment reproducibility.

A replay dataset is identified by a manifest, not by an informal query.

### L7 — Model / Experiment Artifacts
Owner: D13 Learning / Experimentation

Purpose:
- experiment artifacts;
- candidate model versions;
- calibration reports;
- drift evidence;
- champion/challenger records.

Every model artifact points back to the exact dataset manifest.

### L8 — Audit / Evidence
Owner: D17 Evidence / Audit

Purpose:
- append-only/tamper-evident record of material actions, approvals, decisions and closure evidence.

Audit stores references and required facts, not raw secrets.

## 5. Major data classes

### Reference data
Includes:
- canonical instrument definitions;
- provider/venue aliases;
- precision;
- contract metadata;
- effective-dated calendars.

Versioned by effective time.

### Trades / quotes
Key dimensions:
- provider;
- instrument;
- event time;
- provider sequence/event ID.

Retention depends on rights.

### Order book
High-volume and highly provider-specific.

Required:
- provider;
- instrument;
- sequence;
- depth/channel;
- snapshot/delta relationship.

Raw retention is strictly rights-driven.

### Bars / aggregates
Must distinguish:
- provider-native;
- internally derived;
- quote-based;
- trade-based;
- proxy-volume-derived.

### Macro vintages
Never overwrite historical observations.

Keep:
- initial release;
- value known at each vintage;
- later revisions;
- release/observed timestamps.

Backtests use only the vintage known at simulated decision time.

### Features / evidence
Every feature is keyed by:
- feature definition/version;
- entity/instrument;
- event/as-of time;
- dataset version.

### Execution state events
Includes:
- intent;
- acknowledgement;
- reject;
- cancel;
- fill;
- reconciliation;
- position transition.

These are audit-critical and long-lived.

### Risk / Firewall events
Includes:
- risk verdict;
- risk budget;
- firewall verdict;
- rejection reason;
- policy version.

### Audit / Evidence
Append-only and correlation-ID based.

## 6. Corrections, late data and revisions

### Market data

Provider corrections never silently overwrite previously observed events.

Use explicit:
- correction;
- cancel/tombstone;
- replacement;
- linkage to original event.

Current projections may reflect the latest accepted state, but replay must be able to reconstruct what was known earlier.

### Macro data

Initial release and every later revision are separate vintages.

Latest revised values must never leak backward into historical replay.

### Reference data

Instrument/calendar/precision changes are effective-dated and versioned.

## 7. Replay contract

Every replay/backtest manifest includes:

- replay ID;
- time range;
- instrument/series scope;
- raw/canonical dataset versions;
- schema versions;
- quality-rule versions;
- feature-definition versions;
- config version;
- code/artifact version;
- model versions when used;
- clock mode;
- rights class;
- integrity hashes.

Clock modes:
- EVENT_TIME;
- RECEIVE_TIME when required;
- CONTROLLED_SIMULATION_CLOCK.

Look-ahead rule:

> Replay may expose only information whose release/observed time is less than or equal to simulated decision time.

Stochastic components require recorded seed/version.

## 8. Operational state vs historical truth

Examples:

- current position = mutable projection; fills/reconciliation events = authoritative history;
- current order book = projection; retained snapshot/delta history = replay evidence;
- latest macro value = projection; vintage history = historical truth;
- current risk exposure = projection; risk/firewall verdicts = audit history.

This prevents an operational cache/store from becoming an accidental audit database.

## 9. Licensing-aware retention

Every dataset receives a rights classification such as:

- `UNRESTRICTED_INTERNAL`
- `SOURCE_ATTRIBUTION_REQUIRED`
- `NON_DISPLAY_INTERNAL`
- `PROVIDER_RESTRICTED`
- `RETENTION_LIMITED`
- `DERIVED_ONLY`
- `CONTRACT_REVIEW`

Rules:
- retention is provider/dataset-specific;
- raw retention is never globally assumed;
- if raw retention is prohibited, retain only permitted derived data/metadata and non-content audit references;
- audit facts remain even when restricted raw content must expire;
- redistribution/export stays disabled unless explicitly licensed.

## 10. Security classification

Logical access classes:

- PUBLIC_REFERENCE
- INTERNAL
- PROVIDER_RESTRICTED
- SENSITIVE_INTERNAL
- RESTRICTED_INTERNAL
- SECRET

Secrets/tokens/API keys never enter analytical market datasets.

Execution/account state is sensitive.  
Audit/security evidence is restricted.  
Provider raw data may be contract-restricted.

## 11. Integrity and recovery

Required controls:
- content hashes/checksums;
- schema validation;
- versioned manifests;
- duplicate/gap detection;
- backup verification;
- restore validation.

Recovery rules:
- operational projections are rebuildable;
- restored data is not trusted until integrity validation passes;
- incomplete/corrupt restore enters quarantine;
- backups do not bypass provider retention/licensing obligations.

## 12. Logical partitioning/indexing requirements

Physical technology is deferred, but logical access patterns are known.

Typical keys include:
- event date/time;
- canonical instrument ID;
- provider/venue;
- series ID;
- feature set/version;
- account/portfolio scope;
- task/correlation ID.

P02-H will quantify volumes/latency.  
P04 will select concrete storage/stream technologies.

## 13. Architecture boundaries

Provider-specific schemas stop at D02.

Canonical market history is owned by D03/D04.

Quality/provenance is owned by D05.

Feature lineage is owned by D06.

Execution state history is owned by D12.

Risk/firewall history is owned by D10/D11.

Audit references are owned by D17.

No shared table may become an undeclared cross-domain API.

## 14. Deferred decisions

P02-C intentionally does not choose:
- PostgreSQL or any other database;
- time-series database;
- object storage;
- stream broker;
- cache;
- feature-store product;
- cloud provider.

These are implementation choices for later architecture/engineering tasks.

## 15. Downstream use

P02-D consumes the evidence/feature/replay model.

P02-E consumes operational + execution/risk event-history rules.

P02-F maps agent access to these data boundaries.

P02-G defines physical network/process/storage isolation.

P02-H sizes storage, throughput and retention.

P02-I validates replayability, portability and recovery before G2.

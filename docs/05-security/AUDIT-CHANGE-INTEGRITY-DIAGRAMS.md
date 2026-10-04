# NEXUS QUANT — Audit & Change Integrity Diagrams

STATE = P03-E CANONICAL_BASELINE
TASK = `FIN-P03-WE-001`
BASELINE = `FROZEN_G2`

## 1. Canonical audit flow

~~~mermaid
flowchart LR
    Source[Human / Agent / Service / CI]
    Domain[Domain Action]
    Event[Canonical Audit Event]
    Validate[Schema + Required Fields]
    Digest[Digest / Chain Position]
    Store[Append-only Evidence Store Class]
    Manifest[Integrity Checkpoint / Manifest]
    Verify[Independent Verification]
    Alert[Alert / Incident]

    Source --> Domain --> Event --> Validate --> Digest --> Store --> Manifest --> Verify
    Validate -->|invalid / incomplete critical event| Alert
    Verify -->|gap / mismatch| Alert
~~~

Critical canonical history is appended, not silently edited.

## 2. Actor attribution

~~~mermaid
flowchart LR
    Human[Initiating Human]
    Task[Task / Run]
    Agent[Agent]
    Tool[Tool / Service]
    Action[Normalized Action]
    Authz[Authorization Decision]
    Result[Result]
    Audit[Audit Event]

    Human --> Task --> Agent --> Tool --> Action --> Authz --> Result --> Audit
    Task --> Audit
    Agent --> Audit
    Tool --> Audit
    Authz --> Audit
~~~

Delegation preserves initiator → delegator → executor.

## 3. High-risk change control

~~~mermaid
flowchart LR
    Maker[Maker]
    Change[Exact Change + Digest]
    Evidence[Evidence / Rollback]
    Checker[Checker / Human Gate]
    Veto[A5 / A8 State]
    Apply[Apply Exact Approved Change]
    Verify[Post-change Verification]
    Audit[Audit / Evidence]
    Deny[DENY]

    Maker --> Change --> Evidence --> Checker
    Change --> Veto
    Checker --> Apply
    Veto --> Apply
    Apply --> Verify --> Audit
    Checker -->|deny / expired / mismatch| Deny
    Veto -->|active veto| Deny
    Apply -->|digest differs| Deny
~~~

Approval is one-use and binds exact resource, environment and digest.

## 4. Tamper-evident chain

~~~mermaid
flowchart LR
    E1[Event n-1] --> D1[Digest n-1]
    E2[Event n] --> D2[Digest n]
    D1 --> D2
    S[Stream ID + Schema] --> D2
    D2 --> CP[Checkpoint / Manifest]
    CP --> Trust[Protected Trust Anchor / Attestation Direction]
~~~

Conceptual: `digest_n = H(event_n || digest_(n-1) || stream_id || schema_version)`.

## 5. Separation of duties

~~~mermaid
flowchart TB
    Writer[Audit Writer]
    Reader[Investigator / Reader]
    Admin[Audit Platform Admin]
    A10[A10 Evidence Verifier]
    Store[Canonical Evidence]

    Writer -->|append only| Store
    Reader -->|scoped read| Store
    Admin -->|operate platform| Store
    A10 -->|verify completeness/integrity| Store

    Block1{{No writer delete/overwrite}}
    Block2{{No reader mutation}}
    Block3{{No audit-admin business authority by inheritance}}

    Writer -. forbidden .-> Block1
    Reader -. forbidden .-> Block2
    Admin -. forbidden .-> Block3
~~~

## 6. Audit failure behavior

~~~mermaid
flowchart LR
    Action[Requested Action]
    Risk{HIGH / CRITICAL privileged or financial?}
    AuditHealth{Required Audit Durable?}
    Allow[Proceed]
    Buffer[Bounded Degraded / Buffer]
    Block[BLOCK / SAFE_MODE]
    Alert[Security Alert]

    Action --> Risk
    Risk -->|yes| AuditHealth
    AuditHealth -->|yes| Allow
    AuditHealth -->|no| Block --> Alert
    Risk -->|no| AuditHealth
    AuditHealth -->|no but policy permits| Buffer --> Alert
~~~

Logging failure never converts DENY into ALLOW.

## 7. Correction / revision model

~~~mermaid
flowchart LR
    Old[Prior Canonical Event]
    Correction[Correction / Override Event]
    Link[Link to Prior Event + Reason + Evidence]
    NewState[Derived Current State]

    Old --> Link
    Correction --> Link --> NewState
~~~

The old observation remains preserved; current state is derived from the linked history.

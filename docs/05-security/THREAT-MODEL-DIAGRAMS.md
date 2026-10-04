# NEXUS QUANT — Threat Model Diagrams

STATE = P03-A CANONICAL_BASELINE
TASK = FIN-P03-WA-001
BASELINE = FROZEN_G2

These diagrams refine the frozen G2 trust boundaries for threat analysis. They do not change the architecture baseline.

## 1. Trust zones and external attack surface

~~~mermaid
flowchart LR
    U[Z0 User Edge] --> A[Z1 Application Ingress]
    A --> C[Z2 Control Plane]
    C --> D[Z3 Data Plane]
    C --> E[Z4 Execution Enclave]
    E --> S[Z5 Security / Secrets]
    D --> O[Z6 Observability / Audit]
    C --> O
    E --> O
    S --> O
    O --> R[Z7 Backup / DR]
    D --> R
    E --> R

    EXT1[Market / Macro / News / On-chain Providers] --> D
    EXT2[Model / Tool / MCP Services] <--> C
    EXT3[GitHub / CI / Package Registries] --> C
    E <--> EXT4[Future Broker / Exchange]
    A --> EXT5[Notification Channels]

    X1((T001/T002/T032)) -. User/Auth attack surface .-> A
    X2((T008-T013)) -. Agent/Tool attack surface .-> C
    X3((T014-T018)) -. Data integrity attack surface .-> D
    X4((T019-T024)) -. Execution safety attack surface .-> E
    X5((T005-T007)) -. Secret attack surface .-> S
    X6((T028/T029)) -. Audit attack surface .-> O
    X7((T030/T031)) -. Recovery attack surface .-> R
    X8((T025-T027)) -. Supply-chain attack surface .-> EXT3
~~~

Security rule: no public, UX, model, tool or agent text path directly reaches broker/exchange execution.

## 2. Agent / LLM / Tool Gateway threat path

~~~mermaid
flowchart LR
    Data[Untrusted Web / News / Email / PDF / Repo / MCP Output]
    Agent[Agent / LLM Runtime]
    Kernel[Governance Kernel]
    Gate[Tool Gateway]
    Policy[Task + Agent + Resource + Environment Policy]
    A8[A8 Security Veto]
    A5[A5 Risk Veto]
    Tool[Allowed Tool / Domain API]
    Q[Quarantine]
    Audit[Z6 Audit / Evidence]

    Data --> Agent
    Agent --> Kernel
    Kernel --> Gate
    Policy --> Gate
    A8 --> Gate
    A5 --> Gate
    Gate -->|authorized| Tool
    Gate -->|prompt injection / mismatch / invalid schema| Q
    Agent --> Audit
    Gate --> Audit
    Q --> Audit

    T8((T008 Prompt Injection)) --> Agent
    T9((T009 Tool/MCP Poisoning)) --> Gate
    T10((T010 Excessive Agency)) --> Policy
    T11((T011 Provider Compromise)) --> Agent
    T12((T012 Checkpoint Poisoning)) --> Kernel
~~~

Invariant: model output can propose; deterministic authorization decides.

## 3. Market-data integrity and provenance threat path

~~~mermaid
flowchart LR
    P[External Provider]
    L0[L0 Edge Capture]
    L1[L1 Raw Evidence]
    L2[L2 Canonical Events]
    L3[L3 Quality / Provenance]
    Q{Eligible?}
    L5[L5 Feature / Evidence]
    Reject[Quarantine / Fail Closed]
    Signal[Downstream Decision]

    P --> L0
    L0 --> L1
    L0 --> L2
    L2 --> L3
    L3 --> Q
    Q -->|yes| L5
    Q -->|unknown / stale / poisoned / divergent| Reject
    L5 --> Signal

    T14((T014 Poisoning)) --> P
    T15((T015 Replay/Stale)) --> L2
    T16((T016 Gap/Duplicate/Correction)) --> L2
    T17((T017 Revision Leakage)) --> L1
    T18((T018 Lineage Tamper)) --> L5
~~~

Invariant: critical unknown/quarantined data cannot silently flow as valid.

## 4. Risk / Firewall / Execution threat path

~~~mermaid
flowchart LR
    Signal[SignalCandidate]
    Risk[A5 Risk]
    RV{RiskVerdict}
    Intent[ProposedTradeIntent]
    FW[Pre-Trade Firewall]
    FV{FirewallVerdict}
    OMS[A6 OMS]
    Route[RouteAttempt]
    Broker[Broker / Exchange]
    Recon[Reconciliation]
    Unknown[UNKNOWN]
    Halt[HALT / SAFE_MODE]
    Audit[Audit]

    Signal --> Risk
    Risk --> RV
    RV -->|allow/reduce| Intent
    RV -->|reject/halt| Halt
    Intent --> FW
    FW --> FV
    FV -->|approve| OMS
    FV -->|reject/halt| Halt
    OMS --> Route
    Route --> Broker
    Broker --> Recon
    Recon --> OMS
    Route -->|timeout / uncertain ack| Unknown
    Unknown --> Recon
    Unknown -. no blind retry/reroute .-> Halt

    T19((T019 Veto Bypass)) --> RV
    T20((T020 Duplicate Order)) --> OMS
    T21((T021 Blind Reroute)) --> Unknown
    T22((T022 State Tamper)) --> Recon
    T23((T023 Stale Verdict Replay)) --> FW
    T24((T024 Capability/Precision Manipulation)) --> Route

    Risk --> Audit
    FW --> Audit
    OMS --> Audit
    Recon --> Audit
~~~

Invariant: UNKNOWN is neither success nor rejection; reconcile before new exposure.

## 5. Supply-chain promotion threat path

~~~mermaid
flowchart LR
    Src[Source]
    Dep[Dependencies / Plugins]
    CI[CI / Trusted Builder]
    Scan[SAST / CVE / Policy]
    SBOM[SBOM]
    Artifact[Build Artifact]
    Prov[Provenance / Signature]
    Promote[Environment Promotion]
    Block[BLOCK]

    Src --> CI
    Dep --> CI
    CI --> Scan
    Scan --> SBOM
    SBOM --> Artifact
    Artifact --> Prov
    Prov -->|verified| Promote
    Prov -->|missing / mismatch| Block

    T25((T025 Compromised Dependency)) --> Dep
    T26((T026 CI Token/Workflow Compromise)) --> CI
    T27((T027 Artifact/SBOM Substitution)) --> Prov
~~~

P03 defines the security baseline; P04 activates concrete scanning, SBOM, provenance and reproducible-build enforcement.

## 6. Backup / restore threat path

~~~mermaid
flowchart TB
    Incident[Failure / Security Incident]
    Halt[HALTED / SAFE_MODE]
    Backup[Z7 Backup / DR]
    Stage[Restore Staging / Quarantine]
    Integrity[Manifest / Hash / Policy Validation]
    Security[Identity / Secret / Credential Revalidation]
    External[Broker / Provider Truth Reconciliation]
    Data[Data Quality / Provenance Validation]
    Audit[Audit Integrity Validation]
    Gate[Fresh Risk / Security / Authorization]
    Normal[NORMAL]

    Incident --> Halt
    Halt --> Backup
    Backup --> Stage
    Stage --> Integrity
    Integrity --> Security
    Security --> External
    External --> Data
    Data --> Audit
    Audit --> Gate
    Gate --> Normal

    T30((T030 Corrupt Restore)) --> Stage
    T31((T031 Shared Failure Domain)) --> Backup
    T28((T028 Audit Tamper)) --> Audit
    T29((T029 Telemetry Blindness)) --> Gate
~~~

Invariant: restored state is not execution authorization.

## 7. Diagram-to-threat coverage

| Diagram | Primary threats |
|---|---|
| Trust zones / external surface | T001–T035 |
| Agent / LLM / Tool Gateway | T008–T013, T019 |
| Data integrity / provenance | T014–T018 |
| Risk / Firewall / Execution | T019–T024 |
| Supply chain / promotion | T025–T027 |
| Backup / restore | T028–T031 |

All diagrams preserve the FROZEN_G2 authority and trust-zone model.

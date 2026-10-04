# NEXUS QUANT — P02 Architecture Diagrams

STATE = P02-I REVIEW ARTIFACT  
TASK = `FIN-P02-WI-001`  
GATE = `G2_ARCHITECTURE_FREEZE`

These diagrams are logical architecture views. They do not select a cloud, region, database, queue, broker, model vendor or production account.

---

## 1. System Context

```mermaid
flowchart LR
    Owner[Owner / Small Team] --> App[NEXUS QUANT Application]
    App --> DataProviders[Market / Macro / News / On-chain Data Providers]
    App --> ModelTools[Model / Tool Services]
    App --> Broker[Future Broker / Exchange APIs]
    App --> Notify[Notification Channels]
    Gov[GitHub + Linear Governance] --> App
    App --> Audit[Evidence / Audit]
    Broker -. Disabled until later gates .-> App
```

Key rule: external systems are providers of data/services. They do not define NEXUS QUANT authority.

---

## 2. Containers / Logical Modules

```mermaid
flowchart TB
    UI[Application API / Persian RTL UX]
    Control[Governance + Agent Control Plane]
    Ref[Instrument / Reference Data]
    Adapters[Market Data Adapters]
    Canon[Canonical Market Events]
    Quality[Data Quality / Provenance]
    Raw[Raw / Historical / Replay Storage]
    Features[Feature / Evidence Foundation]
    Intel[Market Intelligence]
    Quant[Quant / Strategy]
    Signal[Signal / Probability / Explainability]
    Risk[Portfolio Risk]
    FW[Pre-Trade Firewall]
    OMS[Execution / OMS / Reconciliation]
    Learn[Learning / Experimentation]
    Sec[Security / Identity / Secrets]
    Ops[Operations / Observability / Recovery]
    Audit[Evidence / Audit Ledger]

    UI --> Control
    UI --> Signal
    UI --> Risk

    Adapters --> Canon
    Ref --> Adapters
    Ref --> Canon
    Canon --> Quality
    Canon --> Raw
    Quality --> Features
    Raw --> Features
    Features --> Intel
    Features --> Quant
    Intel --> Signal
    Quant --> Signal
    Signal --> Risk
    Risk --> FW
    FW --> OMS

    Raw --> Learn
    Features --> Learn
    Quant --> Learn

    Sec --> Control
    Sec --> OMS
    Ops --> Risk
    Ops --> FW
    Ops --> OMS

    Control --> Audit
    Signal --> Audit
    Risk --> Audit
    FW --> Audit
    OMS --> Audit
    Learn --> Audit
```

Logical modules do not imply one microservice per box.

---

## 3. Data Flow

```mermaid
flowchart LR
    P[External Provider]
    L0[L0 Edge Capture]
    L1[L1 Raw Evidence]
    L2[L2 Canonical Events]
    L3[L3 Quality / Provenance]
    L4[L4 Operational Projections]
    L5[L5 Feature / Evidence]
    L6[L6 Research / Replay Manifests]
    L7[L7 Model / Experiment Artifacts]
    L8[L8 Audit / Evidence]

    P --> L0
    L0 --> L1
    L0 --> L2
    L2 --> L3
    L2 --> L4
    L3 --> L4
    L2 --> L5
    L3 --> L5
    L1 --> L6
    L2 --> L6
    L3 --> L6
    L5 --> L6
    L6 --> L7

    L0 --> L8
    L2 --> L8
    L3 --> L8
    L5 --> L8
    L6 --> L8
    L7 --> L8
```

Corrections/revisions append new truth versions rather than silently rewriting what was previously observed.

---

## 4. Decision Flow

```mermaid
flowchart LR
    Q[Quality-qualified Evidence]
    T[Technical Families]
    O[Order Flow / Liquidity]
    M[Macro / Fundamental]
    N[News / Sentiment]
    I[Intermarket]
    MM[Market Memory]
    Fusion[Correlation-aware Evidence Fusion]
    Prob[Empirical Probability / Calibration]
    Explain[Structured Explainability]
    Decision{Signal Candidate}
    Wait[WAIT]
    NoTrade[NO_TRADE]
    Long[LONG_CANDIDATE]
    Short[SHORT_CANDIDATE]

    Q --> T
    Q --> O
    Q --> M
    Q --> N
    Q --> I
    Q --> MM

    T --> Fusion
    O --> Fusion
    M --> Fusion
    N --> Fusion
    I --> Fusion
    MM --> Fusion

    Fusion --> Prob
    Fusion --> Explain
    Prob --> Decision
    Explain --> Decision

    Decision --> Wait
    Decision --> NoTrade
    Decision --> Long
    Decision --> Short
```

Multiple correlated indicators do not count as multiple independent confirmations.

Numeric probability is empirical/calibrated or unavailable; it is never generated from LLM narrative confidence.

---

## 5. Execution Path

```mermaid
flowchart LR
    Signal[SignalCandidate]
    Risk[Independent Risk Engine]
    RV{RiskVerdict}
    Intent[ProposedTradeIntent]
    FW[Deterministic Pre-Trade Firewall]
    FV{FirewallVerdict}
    Approved[ApprovedTradeIntent]
    OMS[OMS]
    Route[RouteAttempt]
    Adapter[Execution Adapter]
    Broker[Broker / Exchange]
    Recon[Reconciliation]
    Audit[Audit / Evidence]

    Signal --> Risk
    Risk --> RV
    RV -->|ALLOW / REDUCE| Intent
    RV -->|REJECT / HALT| Audit
    Intent --> FW
    FW --> FV
    FV -->|APPROVE| Approved
    FV -->|REJECT / HALT| Audit
    Approved --> OMS
    OMS --> Route
    Route --> Adapter
    Adapter --> Broker
    Broker --> Recon
    Recon --> OMS

    Signal --> Audit
    RV --> Audit
    FV --> Audit
    OMS --> Audit
    Recon --> Audit
```

No Strategy, Agent, UX component or model has a direct broker path.

Timeout is not proof of rejection. UNKNOWN execution state requires reconciliation before retry/reroute.

---

## 6. Recovery Path

```mermaid
flowchart TB
    Failure[Failure / Incident Detected]
    Halt[HALTED or SAFE_MODE]
    Sec[Restore Identity / Security / Control]
    Config[Validate Policy + Config Versions]
    State[Restore Execution / Audit State]
    Broker[Reconcile Broker Truth]
    Data[Restore / Validate Market + Quality State]
    Rebuild[Rebuild Projections / Read Models]
    Agents[Revalidate Agent Checkpoints / Tools / Permissions]
    Health[Health + Integrity Checks]
    ReadOnly[Enable Read-only / Research Paths]
    Gate[Fresh Risk / Security / Approval Checks]
    Normal[NORMAL]

    Failure --> Halt
    Halt --> Sec
    Sec --> Config
    Config --> State
    State --> Broker
    Broker --> Data
    Data --> Rebuild
    Rebuild --> Agents
    Agents --> Health
    Health --> ReadOnly
    ReadOnly --> Gate
    Gate --> Normal
```

Infrastructure recovery is not execution authorization. External execution truth must be reconciled first.

---

## 7. Agent Interaction / Authority

```mermaid
flowchart TB
    Owner[Owner / Governance]
    A0[A0 Governance / Orchestrator]
    A1[A1 Architecture]
    A2[A2 Data]
    A3[A3 Market Intelligence]
    A4[A4 Quant]
    A5[A5 Risk Veto]
    A6[A6 Execution]
    A7[A7 Learning]
    A8[A8 Security Veto]
    A9[A9 Operations]
    A10[A10 Evidence / Audit]
    Specialists[Bounded Specialists]
    Kernel[Governance Kernel / Tool Gateway]
    Domains[Canonical Domain APIs]

    Owner --> A0
    A0 --> A1
    A0 --> A2
    A0 --> A3
    A0 --> A4
    A0 --> A5
    A0 --> A6
    A0 --> A7
    A0 --> A8
    A0 --> A9
    A0 --> A10

    A0 --> Specialists
    A1 --> Kernel
    A2 --> Kernel
    A3 --> Kernel
    A4 --> Kernel
    A5 --> Kernel
    A6 --> Kernel
    A7 --> Kernel
    A8 --> Kernel
    A9 --> Kernel
    A10 --> Kernel
    Specialists --> Kernel
    Kernel --> Domains

    A5 -. binding veto .-> A6
    A8 -. binding veto .-> Kernel
    A10 -. evidence verification .-> A0
```

Agent consensus cannot override A5 or A8.

Tool availability is not permission.

Specialists are bounded, catalog-listed and ephemeral by default.

---

## Diagram review result

| Diagram | Status |
|---|---|
| System context | PASS |
| Containers/modules | PASS |
| Data flow | PASS |
| Decision flow | PASS |
| Execution path | PASS |
| Recovery path | PASS |
| Agent interaction | PASS |

All seven diagram classes required by the Execution Roadmap are present.

LIVE_TRADING = DISABLED  
AUTO_TRADING = DISABLED

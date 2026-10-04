# NEXUS QUANT — Private Administration & Network Exposure Diagrams

STATE = P03-D IMPLEMENTATION
TASK = `FIN-P03-WD-001`
BASELINE = `FROZEN_G2`

## 1. Exposure model

~~~mermaid
flowchart LR
    Internet[Internet]
    Edge[E0 Public Edge]
    App[E1 Authenticated App Ingress]
    Admin[E2 Private / Identity-Aware Admin]
    Control[Z2 Control Plane]
    Data[Z3 Data Plane]
    Exec[Z4 Execution Enclave]
    Secrets[Z5 Security / Secrets]
    Obs[Z6 Observability / Audit]
    DR[Z7 Backup / DR]

    Internet --> Edge --> App
    App --> Control
    Admin --> Control
    Admin -. exceptional governed .-> Data
    Admin -. exceptional governed .-> Exec
    Admin -. restricted .-> Secrets
    Admin --> Obs
    Admin -. recovery only .-> DR

    Control --> Data
    Control --> Exec
    Exec --> Secrets
    Data --> Obs
    Control --> Obs
    Exec --> Obs
    Secrets --> Obs
    Obs --> DR
~~~

There is no public inbound administrative path to Z2–Z7.

## 2. Administrative authorization path

~~~mermaid
flowchart LR
    Human[Privileged Human]
    Entry[ZTNA / IAP / VPN+Bastion Class]
    Auth[P03-B Identity + Phishing-resistant MFA]
    Device[Device / Security Context]
    Policy[Action + Resource + Environment Policy]
    A8[A8 Security State]
    HG[Human Gate if required]
    Session[Time-bounded Admin Session]
    Target[Authorized Admin Resource]
    Deny[DENY + Audit]

    Human --> Entry --> Auth
    Auth --> Device --> Policy
    A8 --> Policy
    HG --> Policy
    Policy -->|allow| Session --> Target
    Policy -->|deny / stale / mismatch| Deny
~~~

Private connectivity alone never reaches the target.

## 3. Public vs management plane

~~~mermaid
flowchart TB
    Public[Public User Traffic]
    PublicControls[TLS / DDoS / Rate Limit / WAF-API Controls]
    Z1[Z1 Application Ingress]
    UserAPI[User-facing Domain APIs]

    AdminUser[Privileged Administrator]
    PrivateEntry[Private / Identity-aware Admin Entry]
    MgmtAPI[Management APIs / Interfaces]

    Public --> PublicControls --> Z1 --> UserAPI
    AdminUser --> PrivateEntry --> MgmtAPI

    Block{{No public route to native admin ports}}
    Public -. forbidden .-> Block
    Block -. forbidden .-> MgmtAPI
~~~

A hidden admin URL on the public application is not sufficient isolation.

## 4. East-west default-deny

~~~mermaid
flowchart LR
    Caller[Source Workload Identity]
    Policy[Service Policy]
    Env[Environment]
    Action[Exact API / Action]
    Dest[Destination Service]
    Deny[DENY]

    Caller --> Policy
    Env --> Policy
    Action --> Policy
    Policy -->|authorized| Dest
    Policy -->|missing / mismatch| Deny
~~~

Subnet membership is not service authorization.

## 5. Egress paths

~~~mermaid
flowchart LR
    Z3[Z3 Data Plane]
    Z2[Z2 Control Plane]
    Z4[Z4 Execution Enclave]
    DataProviders[Market / Macro / News / On-chain]
    Tools[Model / Tool / MCP]
    Broker[Broker / Exchange]
    Notify[Notification]
    Gateway[Controlled Egress Policy]

    Z3 --> Gateway --> DataProviders
    Z2 --> Gateway --> Tools
    Z4 --> Gateway --> Broker
    Z2 --> Gateway --> Notify
    Z4 --> Gateway --> Notify
~~~

Broker order traffic originates only from Z4.

## 6. Restricted zones

~~~mermaid
flowchart TB
    Internet[Internet / User Edge]
    Z4[Z4 Execution]
    Z5[Z5 Secrets]
    Z7[Z7 Backup / DR]
    Internal[Explicit Internal Policy Paths]
    Admin[Governed E2 Admin Path]

    Internet -. NO PUBLIC INBOUND .-> Z4
    Internet -. NO PUBLIC INBOUND .-> Z5
    Internet -. NO PUBLIC INBOUND .-> Z7
    Internal --> Z4
    Internal --> Z5
    Admin -. exceptional .-> Z4
    Admin -. restricted .-> Z5
    Admin -. recovery only .-> Z7
~~~

## 7. Break-glass lifecycle

~~~mermaid
stateDiagram-v2
    [*] --> Disabled
    Disabled --> Requested: incident / recovery need
    Requested --> Authorized: strong accountable approval
    Requested --> Denied: insufficient evidence
    Authorized --> Active: exact scope + time bound
    Active --> Revoked: task complete / timeout
    Revoked --> Reviewed: evidence + follow-up
    Reviewed --> Disabled
    Denied --> Disabled
~~~

Break-glass cannot bypass A5/A8, Risk/Firewall or grant live trading authority.

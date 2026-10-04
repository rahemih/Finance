# NEXUS QUANT — Secrets & Key Management Diagrams

STATE = P03-C IMPLEMENTATION
TASK = `FIN-P03-WC-001`
BASELINE = `FROZEN_G2`

## 1. Secret resolution boundary

~~~mermaid
flowchart LR
    App[App / Agent / Service]
    Ref[Secret Handle]
    ID[Workload Identity]
    Policy[AuthZ / Environment Policy]
    Vault[Secret Manager / Vault Class]
    KMS[KMS / HSM Class]
    Target[Provider / DB / Broker]
    Audit[Audit]
    Deny[DENY / Quarantine]

    App --> Ref
    App --> ID
    Ref --> Policy
    ID --> Policy
    Policy -->|allowed| Vault
    Policy -->|denied| Deny
    Vault --> KMS
    Vault -->|bounded secret use| Target
    Policy --> Audit
    Vault --> Audit
    KMS --> Audit
~~~

Raw values do not flow through model prompts, ordinary config or evidence.

## 2. Environment isolation

~~~mermaid
flowchart TB
    DEV[DEV namespace / keys]
    TEST[TEST namespace / keys]
    RESEARCH[RESEARCH namespace / keys]
    DEMO[DEMO namespace / keys]
    SHADOW[SHADOW namespace / keys]
    CANARY[CANARY credentials NONE]
    LIVE[LIVE credentials NONE]

    DEV -. code/config promotion only .-> TEST
    TEST -. promotion only .-> RESEARCH
    RESEARCH -. promotion only .-> DEMO
    DEMO -. promotion only .-> SHADOW
    SHADOW -. later gate .-> CANARY
    CANARY -. later gate .-> LIVE
~~~

Secrets and identity authority never ride with artifact promotion.

## 3. Envelope encryption

~~~mermaid
flowchart LR
    Root[Root / Trust Boundary]
    KEK[Environment + Purpose KEK]
    DEK[Versioned DEK]
    Data[Plaintext Data in Process]
    Cipher[Ciphertext + Key Metadata]
    Store[Storage]

    Root --> KEK
    KEK --> DEK
    Data --> DEK
    DEK --> Cipher --> Store
~~~

Root/KEK material remains inside the key-management boundary.

## 4. Secret lifecycle

~~~mermaid
stateDiagram-v2
    [*] --> Issued
    Issued --> Active
    Active --> Rotating: schedule / policy / compromise
    Rotating --> Active: new version verified
    Active --> Revoked: compromise / no longer needed
    Active --> Expired: TTL
    Rotating --> Revoked: old version
    Revoked --> DestroyedOrArchived
    Expired --> DestroyedOrArchived
~~~

## 5. Execution credential boundary

~~~mermaid
flowchart LR
    A6[A6 / OMS]
    Handle[Opaque S5 Handle]
    ExecID[Execution Workload Identity]
    Policy[Exact Provider/Account/Env/Operation Policy]
    Secret[S5 Trading Credential]
    Broker[Broker / Exchange]
    Block[BLOCK]

    A6 --> Handle
    Handle --> Policy
    ExecID --> Policy
    Policy -->|valid| Secret --> Broker
    Policy -->|mismatch / unknown / revoked| Block
~~~

Future S5 credentials are trading-only and no-withdrawal/transfer where provider permissions allow.

## 6. Rotation / compromise

~~~mermaid
flowchart LR
    Detect[Leak / Rotation Trigger]
    Halt[Halt Affected Privileged Path]
    New[Issue New Version]
    Switch[Switch Authorized Consumer]
    Verify[Verify New Version]
    Revoke[Revoke Old]
    Monitor[Monitor Old-Version Rejection]
    Resume[Resume after Evidence]

    Detect --> Halt --> New --> Switch --> Verify --> Revoke --> Monitor --> Resume
~~~

Compromise rotation may favor safety over availability.

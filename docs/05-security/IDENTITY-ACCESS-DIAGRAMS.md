# NEXUS QUANT — Identity & Access Diagrams

STATE = P03-B IMPLEMENTATION
TASK = `FIN-P03-WB-001`
BASELINE = `FROZEN_G2`

## 1. Human authentication and authorization

~~~mermaid
flowchart LR
    Human[Human Principal]
    Auth[Primary Authentication]
    MFA[Phishing-resistant MFA / WebAuthn]
    Session[Governed Session]
    Step[Step-up if Sensitive]
    Authz[Authorization Engine]
    Task[Task / Lock / Gate]
    Role[Role / Capability]
    Env[Environment / Resource]
    Veto[A5 Risk + A8 Security State]
    HG[Human Gate when required]
    Allow[ALLOW]
    Deny[DENY + Audit]

    Human --> Auth --> MFA --> Session
    Session --> Step --> Authz
    Task --> Authz
    Role --> Authz
    Env --> Authz
    Veto --> Authz
    HG --> Authz
    Authz -->|all required terms valid| Allow
    Authz -->|missing / stale / veto / mismatch| Deny
~~~

Default = DENY.

## 2. Principal separation

~~~mermaid
flowchart TB
    Humans[Human Principals]
    Owner[Owner / Governance]
    Sec[Security Operator]
    Ops[Operations Operator]
    Research[Research Operator]
    Auditor[Read-only Auditor]

    Machines[Non-human Principals]
    Core[A0-A10 Core Agents]
    Specialists[Specialists]
    Services[Domain Workloads]
    CI[CI / Build]
    External[External Integrations]

    Humans --> Owner
    Humans --> Sec
    Humans --> Ops
    Humans --> Research
    Humans --> Auditor

    Machines --> Core
    Machines --> Specialists
    Machines --> Services
    Machines --> CI
    Machines --> External

    Boundary{{No ambient credential / role sharing}}
    Humans --> Boundary
    Machines --> Boundary
~~~

Human sessions are not service credentials. Service identities are not interactive user accounts.

## 3. Session lifecycle

~~~mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Authenticated: auth + required MFA
    Authenticated --> Elevated: fresh step-up
    Elevated --> Authenticated: step-up freshness expires
    Authenticated --> Revoked: logout / reset / admin revoke / compromise
    Elevated --> Revoked: security change / compromise / role change
    Authenticated --> Expired: idle or absolute timeout
    Elevated --> Expired: idle or absolute timeout
    Revoked --> Unauthenticated
    Expired --> Unauthenticated
~~~

Privilege change and reauthentication rotate the session identifier.

## 4. Device trust

~~~mermaid
flowchart LR
    Device[Device]
    Register[Register / Observe]
    Risk[Device Risk State]
    Auth[Authentication]
    Step{Step-up required?}
    Session[Session]
    Revoke[Device Revoked / Compromised]
    Deny[Privileged DENY]

    Device --> Register --> Risk
    Risk --> Auth --> Step
    Step -->|yes| Session
    Step -->|no, policy allows| Session
    Risk --> Revoke --> Deny
~~~

Device trust is context only. It never replaces privileged MFA. Country/location is not trusted authorization proof.

## 5. Agent and service permission intersection

~~~mermaid
flowchart LR
    Task[Task Contract]
    Agent[Agent / Specialist Contract]
    Service[Service Identity]
    Tool[Tool Policy]
    Resource[Resource + Environment]
    Risk[A5 State]
    Security[A8 State]
    Gate[Human Gate if required]
    Eval[Deterministic Permission Evaluation]
    API[Authorized Domain API]
    Reject[Reject / Quarantine / Audit]

    Task --> Eval
    Agent --> Eval
    Service --> Eval
    Tool --> Eval
    Resource --> Eval
    Risk --> Eval
    Security --> Eval
    Gate --> Eval
    Eval -->|intersection permits| API
    Eval -->|otherwise| Reject
~~~

No model, framework or external provider can expand authority.

## 6. Recovery / authenticator reset

~~~mermaid
flowchart TB
    Start[Recovery Requested]
    Identify[Verify Existing Recovery Evidence]
    Restricted[Restricted Recovery Mode]
    Review[Step-up / Security Review]
    Reset[Reset / Enroll Authenticator]
    Revoke[Revoke Affected Sessions]
    Audit[High-severity Audit]
    Restore[Restore Allowed Privilege]
    Fail[Fail Closed]

    Start --> Identify
    Identify -->|sufficient| Restricted
    Identify -->|insufficient| Fail
    Restricted --> Review
    Review -->|approved| Reset
    Review -->|denied| Fail
    Reset --> Revoke --> Audit --> Restore
~~~

Security questions and email/SMS-only privileged recovery are forbidden.

## 7. Environment authority

~~~mermaid
flowchart LR
    DEV[DEV]
    TEST[TEST]
    RESEARCH[RESEARCH]
    DEMO[DEMO]
    SHADOW[SHADOW]
    CANARY[CANARY DISABLED]
    LIVE[LIVE DISABLED]

    DEV -. artifact promotion only .-> TEST
    TEST -. artifact promotion only .-> RESEARCH
    RESEARCH -. artifact promotion only .-> DEMO
    DEMO -. governed promotion only .-> SHADOW
    SHADOW -. later gate only .-> CANARY
    CANARY -. later gate only .-> LIVE
~~~

Identity/session/credential authority does not ride with artifact promotion. Lower environments cannot write higher-environment authoritative state.

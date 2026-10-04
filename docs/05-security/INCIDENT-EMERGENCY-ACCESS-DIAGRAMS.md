# NEXUS QUANT — Incident Response & Emergency Access Diagrams

STATE = P03-G IMPLEMENTATION
TASK = `FIN-P03-WG-001`
BASELINE = `FROZEN_G2`

## 1. Incident lifecycle

~~~mermaid
flowchart LR
    Prep[Prepare / Govern]
    Detect[Detect]
    Analyze[Analyze / Declare]
    Contain[Contain]
    Eradicate[Eradicate / Remediate]
    Recover[Staged Recover]
    Review[Post-Incident Review]

    Prep --> Detect --> Analyze --> Contain --> Eradicate --> Recover --> Review --> Prep
~~~

## 2. Incident authority

~~~mermaid
flowchart TB
    A0[A0 Coordination]
    A8[A8 Security]
    A5[A5 Risk]
    A6[A6 Execution]
    A9[A9 Operations]
    A10[A10 Evidence]
    Incident[Incident State]
    Halt[Halt / Safe Mode]
    Recover[Recovery Gate]

    A0 --> Incident
    A8 --> Incident
    A5 --> Incident
    A6 --> Incident
    A9 --> Incident
    A10 --> Incident
    A8 --> Halt
    A5 --> Halt
    A6 --> Halt
    Halt --> Recover
    A8 --> Recover
    A5 --> Recover
    A6 --> Recover
    A9 --> Recover
    A10 --> Recover
~~~

A0 coordination cannot override A5/A8 veto.

## 3. UNKNOWN execution incident

~~~mermaid
flowchart LR
    Submit[Route Attempt]
    Timeout[Timeout / Ambiguous Ack]
    Unknown[UNKNOWN]
    Halt[Stop New Risk-Increasing Orders]
    Recon[Provider Reconciliation]
    Truth{Execution Truth Known?}
    Risk[Fresh Risk + Firewall + Security]
    NewRoute[New Route if Authorized]

    Submit --> Timeout --> Unknown --> Halt --> Recon --> Truth
    Truth -->|no| Recon
    Truth -->|yes| Risk --> NewRoute
~~~

Blind retry/reroute is forbidden.

## 4. Credential compromise

~~~mermaid
flowchart LR
    Detect[Suspected / Confirmed Leak]
    Scope[Classify + Scope]
    Halt[Halt Affected Privileged Path]
    Revoke[Revoke / Disable]
    Rotate[Issue / Rotate Replacement]
    Investigate[Audit Unauthorized Use]
    Validate[Verify Old Credential Rejected]
    Reconcile[Provider / Session Truth]
    Resume[Governed Resume]

    Detect --> Scope --> Halt --> Revoke --> Rotate --> Investigate --> Validate --> Reconcile --> Resume
~~~

## 5. Break-glass access

~~~mermaid
stateDiagram-v2
    [*] --> Disabled
    Disabled --> Requested: incident recovery need
    Requested --> Authorized: unique principal + strong auth + exact scope
    Requested --> Denied
    Authorized --> Active: time bounded
    Active --> Revoked: complete / expiry
    Revoked --> Reviewed
    Reviewed --> Disabled
    Denied --> Disabled
~~~

Break-glass cannot bypass A5/A8 or enable LIVE.

## 6. Recovery gate

~~~mermaid
flowchart TB
    Contained[Incident Contained]
    Identity[Identity / Session Revalidation]
    Secrets[Secrets / Credential Revalidation]
    Network[Network / Admin Path Validation]
    Supply[Artifact / Provenance Validation]
    Audit[Audit Integrity Assessment]
    Data[Data Quality / Provenance Restored]
    External[Provider / Broker / Account Reconciliation]
    A8[A8 Permits]
    A5[A5 Permits]
    Gate[Fresh Human Gate if Required]
    Limited[Limited / Read-Only Recovery]
    Normal[Normal Operation]

    Contained --> Identity --> Secrets --> Network --> Supply --> Audit --> Data --> External --> A8 --> A5 --> Gate --> Limited --> Normal
~~~

## 7. Data poisoning containment

~~~mermaid
flowchart LR
    Alert[Integrity / Divergence Alert]
    Quarantine[Quarantine Source / Range]
    Invalidate[Invalidate Downstream Evidence]
    Preserve[Preserve Raw Observation]
    Scope[Find Affected Features / Signals / Backtests]
    Alternate[Approved Alternate Source if Available]
    Rebuild[Replay / Rebuild]
    Verify[Quality + Provenance Verify]
    Resume[Resume Eligibility]

    Alert --> Quarantine --> Invalidate --> Preserve --> Scope --> Alternate --> Rebuild --> Verify --> Resume
~~~

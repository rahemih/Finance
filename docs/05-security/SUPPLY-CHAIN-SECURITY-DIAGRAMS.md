# NEXUS QUANT — Supply Chain Security Diagrams

STATE = P03-F IMPLEMENTATION
TASK = `FIN-P03-WF-001`
BASELINE = `FROZEN_G2`

## 1. Governed source-to-promotion flow

~~~mermaid
flowchart LR
    Source[Source Revision]
    Deps[Resolved Dependencies + Lockfile]
    CI[Trusted CI / Builder Identity]
    Scan[SAST / SCA / Secret / Policy]
    Build[Immutable Artifact + Digest]
    SBOM[SBOM]
    Prov[SLSA-class Provenance]
    Sign[Signature / Attestation]
    Gate[Verification / Promotion Gate]
    Env[Target Environment]
    Block[BLOCK]

    Source --> CI
    Deps --> CI
    CI --> Scan
    Scan -->|pass| Build
    Scan -->|blocking finding| Block
    Build --> SBOM
    Build --> Prov
    Build --> Sign
    SBOM --> Gate
    Prov --> Gate
    Sign --> Gate
    Build --> Gate
    Gate -->|all evidence matches| Env
    Gate -->|missing / mismatch| Block
~~~

Promotion is artifact-first, not branch-tip-first.

## 2. Dependency trust

~~~mermaid
flowchart LR
    Manifest[Dependency Manifest]
    Lock[Exact Lock / Digest]
    Registry[Approved Registry / Source]
    Evaluate[Vulnerability + Health + License + Security]
    Build[Build Input]
    Deny[DENY / Exception Workflow]

    Manifest --> Lock --> Registry --> Evaluate
    Evaluate -->|acceptable| Build
    Evaluate -->|blocked / unknown high risk| Deny
~~~

Transitive dependencies remain in scope.

## 3. CI privilege boundary

~~~mermaid
flowchart TB
    Untrusted[Untrusted PR / Fork]
    Verify[Verification CI]
    Protected[Protected Promotion CI]
    Runtime[Runtime Identity]
    Secrets[Protected Secrets / Signing Identity]
    Artifact[Artifact Evidence]

    Untrusted --> Verify
    Verify --> Artifact
    Protected --> Artifact
    Secrets --> Protected

    Untrusted -. no protected secrets .-> Secrets
    Verify -. no runtime identity .-> Runtime
    Protected -. separate from .-> Runtime
~~~

CI identity never inherits runtime/business authority.

## 4. SBOM / provenance / signature binding

~~~mermaid
flowchart LR
    Artifact[Artifact Digest]
    SBOM[SBOM Subject]
    Prov[Provenance Subject]
    Sig[Signature / Attestation Subject]
    Verify{All same approved digest?}
    Allow[Promotion Eligible]
    Block[BLOCK]

    Artifact --> Verify
    SBOM --> Verify
    Prov --> Verify
    Sig --> Verify
    Verify -->|yes + policy pass| Allow
    Verify -->|no / missing| Block
~~~

## 5. Exception lifecycle

~~~mermaid
stateDiagram-v2
    [*] --> Requested
    Requested --> Approved: bounded evidence + compensating control
    Requested --> Denied
    Approved --> Active
    Active --> Remediated
    Active --> Expired
    Expired --> Blocked
    Remediated --> Closed
    Denied --> Closed
    Blocked --> Closed
~~~

Permanent blanket waivers are forbidden.

## 6. Compromise response

~~~mermaid
flowchart LR
    Detect[Dependency / Action / Builder Compromise]
    Halt[Halt Promotion]
    Scope[Identify Source / Build / Artifact Digests]
    Revoke[Revoke Affected Identity / Credential]
    Invalidate[Invalidate Artifact Eligibility]
    Repair[Repair Source / Dependency / Workflow]
    Rebuild[Trusted Rebuild]
    Evidence[New SBOM + Provenance + Signature]
    Verify[Independent Verification]
    Resume[Resume]

    Detect --> Halt --> Scope --> Revoke --> Invalidate --> Repair --> Rebuild --> Evidence --> Verify --> Resume
~~~

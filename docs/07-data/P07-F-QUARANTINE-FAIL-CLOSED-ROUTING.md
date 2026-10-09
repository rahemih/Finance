# P07-F — Quarantine & Fail-Closed Routing

Task: `FIN-P07-WF-001`  
Linear: `HOS-208`  
State: IN_PROGRESS  
Lead: A2 Data  
Supporting: A0, A1, A4, A8, A9, A10

## Objective

Turn the canonical P07-E eligibility decision into an explicit safe routing decision with no silent bypass.

## Routing authority

P07-F consumes the P07-E `ProvenanceConfidenceResult`.

- `ELIGIBLE` with no critical reason → `ACCEPTED_DOWNSTREAM`;
- `INELIGIBLE` → `QUARANTINED`;
- `UNKNOWN` → `BLOCKED_UNKNOWN`;
- any explicit critical reason → `QUARANTINED`, even when the incoming status is `ELIGIBLE`.

Only `ACCEPTED_DOWNSTREAM` has `downstream_allowed=true`.

## Routed downstream quality

P07-F exposes the established P06-F `QualityEligibility` interface using the P07-F decision as the evidence boundary:

- `ACCEPTED_DOWNSTREAM` → `ELIGIBLE`;
- `QUARANTINED` → `QUARANTINED`;
- `BLOCKED_UNKNOWN` → `UNKNOWN`.

A critical reason therefore converts even an upstream P07-E `ELIGIBLE` input into routed `QUARANTINED`. This prevents a consumer that relies on the quality contract from bypassing the routing decision.

## Immutable hold evidence

Every non-accepted decision creates a content-addressed `QuarantineRecord` preserving:

- subject identity;
- disposition;
- original P07-E quality status;
- quality policy version;
- P07-E evidence identity;
- sorted unique reason lineage.

Serialized quarantine records verify their declared content identity on read. Tampering fails closed.

## Reason safety

Critical reason codes must satisfy the versioned policy pattern, be unique and remain within the explicit per-decision limit. P07-F never silently normalizes duplicate reasons into one reason.

## Non-destructive behavior

This reference contract does not delete source data. It separates routing eligibility from retention. Production quarantine-storage vendor remains unselected.

## Boundaries

P07-G owns dashboards/SLOs. P07-H owns the integrated Trusted Data Gate / G5.

## Safety

Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-G remains blocked until P07-F canonical closure.

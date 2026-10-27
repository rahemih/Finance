# P23-H — Dangerous-Action / Security UX

Task: `FIN-P23-WH-001`  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WH-001-01` / ACQUIRED  
Claim scope: `SECURITY_UX_VALIDATION_ONLY`

## Security baseline binding

P23-H consumes the canonical G3/P03 security baseline. In particular:
- Human Gate/confirmation must bind exact action/resource/environment/digest/expiry;
- A5 Risk and A8 Security vetoes remain non-bypassable;
- production accounts/credentials/Live/Auto remain disabled.

## Dangerous-action requests

The UX contract covers requests for:
- credential changes;
- permission changes;
- network exposure changes;
- execution-authority changes;
- enabling Live or Auto trading;
- P24 production promotion;
- consequential settings changes.

These are request/confirmation surfaces only. They do not perform the mutation.

## Confirmation contract

Consequential actions require explicit, typed, audit-friendly confirmation and bind exact action, target resource, environment, requested-change digest, expiry and provenance. Current session validity and authorization must be checked server-side. Client-side confirmation can never authorize an action.

Expired/revoked sessions deny. Permission-denied states cannot masquerade as success. Network location is never authorization.

## Secret handling

Raw secrets are never rendered and browser storage for secrets is forbidden.

## Safety

UX confirmation grants no Owner, Risk, Security, execution or P24 authority. A5/A8 vetoes remain intact. Emergency access cannot enable Live. No credential/network/permission/execution mutation is implemented here.

# P23-H — Dangerous-Action / Security UX

Task: `FIN-P23-WH-001`  
Status: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P23-WH-001-01` / RELEASED  
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


## Canonical closure evidence

- implementation PR #485 = MERGED;
- final implementation head = `53a0d4b52cf035132e29090e7195644571a071ff`;
- implementation Governance = `40499843127` / SUCCESS;
- implementation artifact = `12731659152` / `sha256:226b0204dbccd196b3f6fae3399be7d4770d837ae919fb1fc3f7148f1ead506f`;
- policy ID = `17682bbc3cd6e38cda974a4df30e5b3244cc96aa8b379241b5026dd4c017fef2`;
- evidence ID = `e3aca1e988bdc1098b0b756255727a3754b5a4d84346e199df373ce29e3eac04`;
- deterministic evidence SHA256 = `cb52eafaed56acf21bf53f9dc1681b01c651043dcd4ac24eb4cb13681c13a47f`;
- implementation merge = `24893b096444891084fb4ced8402cd1dba3631ea`;
- post-merge Governance = `40500085821` / SUCCESS;
- post-merge artifact = `12731484751` / `sha256:5fa353434fc99877f1dcd01987b32e84aa60e7140640d9bc869329fb1010191c`;
- post-merge Branch Hygiene = `40500085833` / SUCCESS.

P23-I = READY_NOT_STARTED.  
P24 = NOT_STARTED.  
LIVE_TRADING / AUTO_TRADING = DISABLED.

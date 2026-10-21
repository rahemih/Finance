# P20-C — Forex Execution Adapter

Task: `FIN-P20-WC-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Dependency: P20-A..P20-B CANONICAL_COMPLETE

## Objective

Implement the deterministic Forex execution-adapter boundary against P20-A without selecting a production broker or creating any network, credential, account, funding or real-order authority.

## Scope

P20-C owns:
- Forex-only canonical intent binding;
- deterministic quantity-step/minimum validation;
- deterministic price-tick and pip geometry validation;
- deterministic submit and cancel envelopes;
- reference/sandbox ACK, REJECT and CANCEL_ACK normalization;
- exact lineage to P20-A adapter contract and binding identities.

It does not own OMS state, runtime retries, reconciliation, execution-quality metrics or broker certification.

## Broker boundary

Production Forex broker = NOT_SELECTED. Owner/entity jurisdiction is not inferred. No account opening, KYC, credentials, funding, network call or real order is performed by P20-C.

The `forex-reference-sandbox` descriptor is a deterministic test boundary only and is not a hidden production-broker decision.

## Safety boundary

- broker selection = NOT_SELECTED;
- credential mode = NONE;
- network mode = DISABLED;
- external order submission = false;
- Live execution authority = false;
- OMS state authority = false;
- retry authority = false;
- reconciliation authority = false;
- P20-D = READY_NOT_STARTED;
- P20-E..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #415 = MERGED;
- implementation head = `1da1725b68725dcd7a200cd8d702dba61441ec2c`;
- implementation Governance = `39564909377` / SUCCESS;
- implementation artifact = `12329247886` / `sha256:d9196a17635707ca6cbe813306b8b28ce796714ac4ed064c68d53983dceb840a`;
- implementation merge SHA = `20fe8e249c9cabb3266e5f9fc3b663858c5145ee`;
- post-merge Governance = `39565117584` / SUCCESS;
- post-merge artifact = `12330070212` / `sha256:3b4cd333cc618740e3d624ebf05ff51dfe518857c28105f722d96e1d933504ec`;
- post-merge Branch Hygiene = `39565117522` / SUCCESS;
- lock = RELEASED;
- P20-D = READY_NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

P20-C canonical completion grants no production broker selection, credential/network access or Live execution authority.

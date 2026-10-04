# Architecture Decision Records (ADR)

TASK = `FIN-P02-WA-001`

## Purpose

This directory is the canonical record of material architecture decisions.

An ADR is required when a decision:
- changes a cross-domain contract;
- creates/removes a runtime boundary;
- changes provider portability;
- changes security/risk authority;
- changes replay/recovery guarantees;
- introduces a material operational/cost burden;
- supersedes a previous architectural assumption.

## Status lifecycle

Allowed statuses:
- `PROPOSED`
- `ACCEPTED`
- `REJECTED`
- `SUPERSEDED`
- `DEPRECATED`

Only `ACCEPTED` ADRs are binding.

## Numbering

Format:

`ADR-NNNN-short-title.md`

Numbers are monotonic and never reused.

## Required sections

Each ADR must contain:
1. Status
2. Context
3. Decision
4. Alternatives considered
5. Consequences
6. Risks / mitigations
7. Validation / evidence
8. Rollback / supersession
9. Related tasks / gates

## Governance

- A1 owns architecture consistency.
- A5 has veto on Risk-boundary regressions.
- A8 has veto on Security-boundary regressions.
- A9 reviews operational complexity/recovery.
- A10 verifies evidence and traceability.
- A0 coordinates task/lock/gate state.

No ADR can authorize Live/Auto Trading by itself.

## Supersession

A later ADR may supersede an earlier ADR only by:
- referencing the prior ADR;
- explaining the reason;
- documenting migration/compatibility;
- updating the prior ADR status to `SUPERSEDED`.

Historical ADRs are never deleted.

## Foundational ADRs

- ADR-0001 — Modular Core First
- ADR-0002 — Provider Portability & Canonical Contracts
- ADR-0003 — Independent Risk / Firewall Authority
- ADR-0004 — Event-Time, Provenance & Replay
- ADR-0005 — Environment Isolation & Fail-Closed States
- ADR-0006 — Bounded Agent Authority

# ADR-0003 — Independent Risk / Firewall Authority

Status: ACCEPTED  
Task: `FIN-P02-WA-001`

## Context

Strategies, models, agents and execution adapters can all make incorrect decisions. Safety cannot depend on the same component that creates the trading intent.

## Decision

Risk Engine and Pre-Trade Firewall are independent authorities.

They may veto or reduce intents. Strategy/Quant/AI/Execution cannot bypass them.

Risk cannot silently raise its own ceilings.

## Alternatives considered

- Risk checks embedded only inside strategy code — rejected due conflict of authority.
- Execution adapter decides final safety — rejected because adapter responsibility is execution semantics, not portfolio policy.

## Consequences

Positive:
- deterministic final safety boundary;
- clearer audit;
- easier kill-switch implementation.

Negative:
- additional contracts and state synchronization are required.

## Risks / mitigations

Risk: stale Risk state blocks good trades.  
Mitigation: explicit freshness rules, fail-closed reason codes and observability.

## Validation / evidence

P02-E must define interfaces and authority. P15/P16 must implement and test the policy/firewall.

## Rollback / supersession

Cannot be weakened without A5 veto review, A8 security review and A10 evidence.

## Related tasks / gates

P02-E, P15, P16, G8.

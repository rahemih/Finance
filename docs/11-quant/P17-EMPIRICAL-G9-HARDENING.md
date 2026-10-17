# P17 Empirical G9 Hardening — FIN-P17-WI-001-R01

State: CANONICAL_COMPLETE after governed merge

## Purpose

The original P17-A..P17-I CI evidence remains a deterministic self-test suite. It is intentionally retained, but it is no longer sufficient by itself to represent empirical G9 evidence.

FIN-P17-WI-001-R01 adds a second, fail-closed empirical certification path.

## Empirical reference binding

- public-market BTC-USD daily reference observations are checked in with source metadata and `fixture_only=false`;
- the dataset bytes and threshold policy bytes are content-addressed;
- P17-A..P17-H empirical evidence hashes are derived from the reference run, not repeated-character placeholders;
- Strategy Registry and Model Registry identities are constructed from the actual reference dataset, code, policy and D/E/F certificate lineage;
- every benchmark category has a versioned metric schema, unit, comparator and governed threshold;
- every measurement is bound to the dataset and its metric-schema identity;
- fixture-only evidence and degenerate placeholder SHA-256 identities fail closed;
- Governance executes the empirical reference twice and requires byte-identical output.

Required categories remain OOS_EDGE, RISK, ROBUSTNESS, CAPACITY and EXECUTION_REALISM.

## Reference scope

This is a small public-market reference certification used to prove end-to-end empirical binding in CI. It is not a production-scale multi-year research result and is not a profitability guarantee.

## Safety

No broker/exchange routing, execution authority, automatic live promotion, Live Trading or Auto Trading is enabled. P19 is not started by this repair.


## R03 final canonical execution — FIN-P18-WI-001-R03

R03 supersedes R01 as the authoritative empirical G9 implementation path.

The authoritative CI path now calls the actual canonical modules in sequence:
`P17-A Backtest Engine -> P17-B Execution Realism -> P17-C Information Hygiene -> P17-D Walk-Forward -> P17-E Robustness -> P17-F Capacity -> P17-G Strategy Registry -> P17-H Model Registry -> P17-I empirical G9`.

The earlier R01 direct-calculation reference script is retained only as a compatibility/regression surface and explicitly reports `authoritative_g9=false`. Its compatibility metrics are isolated from the canonical metric policy.

Governance `39039915556` and post-merge Governance `39040128212` both passed the canonical pipeline twice with deterministic output. The result remains a small governed public-market reference validation, not a production-scale edge or profitability proof.

P19 remains NOT_STARTED. Live/Auto remain disabled.

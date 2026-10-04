# NEXUS QUANT — Test Harness

STATE = P04-E IMPLEMENTATION
TASK = `FIN-P04-WE-001`
LINEAR = `HOS-176`
DATE = 2026-10-04

## 1. Purpose

P04-E creates the deterministic engineering harness required before market-system implementation.

It provides reusable test primitives only. It does not implement market data, strategy, risk, firewall, OMS or real provider connectivity.

## 2. Canonical primitives

### DeterministicClock

UTC-only test clock with:
- explicit initial instant;
- `now()`;
- positive `advance()`;
- monotonic `set()`.

The harness never depends on wall-clock time for deterministic replay tests.

### DeterministicIdSequence

Stable IDs from an explicit prefix and counter.

The same initial state produces the same ID sequence.

### FixtureLoader

Loads canonical JSON fixtures from repository paths only.

Fixtures are source-controlled evidence and contain no raw secrets or external credentials.

### ReplayTape

Replays ordered events with:
- integer sequence;
- RFC3339/ISO UTC event time;
- event type;
- payload.

It rejects:
- duplicate sequence;
- decreasing sequence;
- decreasing event time.

Replay output can be hashed deterministically.

### ScriptedProviderSimulator

An offline provider simulator driven by a source-controlled outcome script.

Supported submit outcomes in P04-E:
- `ACKNOWLEDGED`
- `REJECTED`
- `TIMEOUT_UNKNOWN`

`TIMEOUT_UNKNOWN` means the harness cannot prove whether the provider accepted/executed the intent. It is not success and not rejection.

While an intent is unresolved:
- blind retry is rejected;
- a second execution-capable submit for that intent is rejected;
- reconciliation is required.

Reconciliation can resolve the provider outcome to a proved state such as:
- `ACKNOWLEDGED`
- `FILLED`
- `CANCELED`
- `REJECTED`

The simulator has no network endpoint and no credential concept.

### FailureInjector

Named deterministic failure points:
- checkpoint name;
- fire-on call number;
- configured exception/message.

This enables repeatable failure-path tests without randomness.

### NetworkDenyGuard

A test context that denies socket connection attempts.

Tests that are intended to be offline can explicitly prove they do not depend on external network availability.

## 3. Determinism contract

A deterministic test must receive all changing inputs explicitly:
- clock;
- IDs;
- replay fixture;
- provider script;
- failure plan;
- configuration.

No deterministic test may require:
- current wall-clock time;
- random global state without fixed seed;
- network availability;
- external provider state;
- undeclared environment secrets.

## 4. Replay contract

Canonical replay ordering is:
1. sequence;
2. event-time monotonicity;
3. original payload.

A valid fixture produces the same normalized event stream and digest on repeated runs.

P04-E replay is an engineering hook, not the final historical replay engine. P06/P15 later own dataset snapshots and backtest/replay execution.

## 5. Execution uncertainty test rule

FROZEN_G2 invariant:

> UNKNOWN is neither success nor rejection.

The harness must make the unsafe behavior impossible to accidentally test as valid:
- timeout creates unresolved state;
- blind retry raises `UnsafeRetryError`;
- reconciliation must occur before continuing that intent.

This is simulator behavior only and does not implement the production OMS.

## 6. Fixtures

Canonical P04-E fixtures:
- `tests/fixtures/foundation/replay-basic.json`
- `tests/fixtures/foundation/provider-unknown.json`

Fixture requirements:
- deterministic;
- small;
- human-reviewable;
- no secrets;
- no live account/provider identifiers;
- no mutable remote dependency.

## 7. CI

The required `governance` status context runs:

```text
python -m unittest discover -s tests/foundation -p 'test_*.py' -v
python scripts/ci/test_harness_evidence.py --output build/test-harness-a.json
python scripts/ci/test_harness_evidence.py --output build/test-harness-b.json
cmp build/test-harness-a.json build/test-harness-b.json
```

The evidence JSON records deterministic fixture/replay digests and harness source digests without timestamps.

The uploaded foundation artifact includes both:
- foundation manifest;
- test-harness evidence.

## 8. Negative-path expectations

CI must prove at least:
- non-monotonic replay is rejected;
- backwards event time is rejected;
- blind retry after UNKNOWN is rejected;
- invalid reconciliation state is rejected;
- configured failure injection fires deterministically;
- network connect is denied inside `NetworkDenyGuard`.

## 9. Safety

External network/provider calls by harness: NONE  
Raw credentials: NONE  
Production accounts: NONE  
Market orders: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 10. Next

After canonical closure only:

`P04-F — Dependency / License / SBOM Governance`

P04-F is not started by this task.

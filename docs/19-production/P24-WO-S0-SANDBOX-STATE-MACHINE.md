# P24-WO-001-R01 — S0 deterministic synthetic order-state rehearsal

**Task:** FIN-P24-WO-001-R01. **Phase:** P24. **Authority:** strictly offline reference code and no network. **Base:** merged #514 plan at main cb7c5aca86ed30769ad0cc855f2a5cfc13740f1a.

## Purpose and non-duplication

The existing 43-test P24-WO preproduction lab already covers quote-age, basic disconnect, unknown ACK, risk-veto and kill-switch reference cases. This addition does **not modify** that baseline. It adds a separate **S0 fixture-only model** of synthetic order *descriptions*: key deduplication, ACK/late ACK, partial fills, cancellation race, unknown outcomes, fixture reconciliation, source licence/UTC checks and tamper-evident hash chaining. This is **not** an order router or a broker adapter.

- Design contract: [24-case Sandbox plan](P24-B-BROKER-SANDBOX-CERTIFICATION-TEST-PLAN.md), SC-01 through SC-21 are modelled only as deterministic *S0 examples*.
- Broker-connected S1 observations, independently broker-authorized order Sandbox S2 cases SC-22, SC-23, SC-24, and funded Live S3 are **NOT_RUN/NOT_CERTIFIED** by this package.
- Python source: packages/production/sandbox_s0_model.py; unit test: tests/p24/test_sandbox_s0_model.py.
- Reuse canonical byte/digest primitives from the original P24-WO lab. No trading SDK, broker credentials, sockets, requests, feeds, MT5 platform integration or clock/numerical normalization.

## Synthetic event contract and reducer

A frozen S0Event has a fixed MARKET → FIXTURE_SERVER + SYMBOL mapping; environment SIMULATED, network DISABLED, credential NONE and external_order_submission false are validated on every event. For S0 fixtures only, timestamps/licences/risk/Owner-like approval are synthetic boolean **assumptions**, never independently attested actual claims.

Event kinds: TICK, INTENT, ACK_UNKNOWN, ACK, PARTIAL_FILL, REJECT, CANCEL_REQUEST, FILL, RECONCILE, DISCONNECT, RECONNECT, HALT, AUDIT_FAIL, SOURCE_EXPIRED, RESET. An INTENT is an **internal test state** with no code path to transmit any order. The reducer records per-key synthetic states and verified fixture units with a deterministic sha256 audit chain and state-seal. It rejects malformed types, cross-market routes, future-trade authority escalation, duplicate event IDs and sequence regression; a gap fails closed.

The reducer's stop modes SAFE_MODE, WAIT_RECONCILIATION and HALTED **never self-reset**. In particular, after UNKNOWN_ACK there is no blind retry; late ACK and fixture reconciliation may update only synthetic records and do not restore new-intent permission. A simulated cancel request is not an actual cancellation; a fill after cancel sets UNKNOWN_OUTCOME. A5 fixture-veto, emergency HALT and audit integrity failures are non-overridable in the synthetic model.

Raw MT5 ticks across the Owner's two read-only Demo terminals earlier showed an approximately +7202 second UTC-interpretation offset with no source attestation. S0 treats timestamp_attested=false as UNVERIFIED_TIME / SAFE_MODE: **no offset substitution, normalizing or freshness-based trade enablement**.

## Coverage / verification / negative tests

The new tests use names test_sc01 through test_sc21 aligned with the 21 S0-design cases, followed by additional strict type, anti-escalation, anti-replay, evidence-determinism and tamper-negative checks. A CI PASS means the **new synthetic software tests** passed; it does not mean 21 broker test scenarios were run or that a production broker Kill Switch works.

SC-01 identity, SC-02 quote freshness, SC-03 source UTC, SC-04 pre-intent disconnect, SC-05 recovery latch, SC-06 wrong symbols, SC-07 cross-market routing, SC-08 missing synthetic gate, SC-09 synthetic risk veto, SC-10 kill latch, SC-11 idempotency, SC-12 unknown ACK, SC-13 late ACK, SC-14 partial fills/remainder reject, SC-15 reject, SC-16 cancel/fill race, SC-17 disconnect after ACK, SC-18 pending-intent halt, SC-19 changed server rejection, SC-20 hash-chain tamper, SC-21 source-rights expiration.

Objective software evidence: python -m unittest discover -s tests/p24 -p 'test_*.py' -v (included in existing protected Governance Verify); strict Pyright; same deterministic s0_reference_evidence() repeated twice yields identical 64-char SHA256 evidence_id and report, actual_broker_connections=0, actual_broker_orders=0, real_pnl_measured=false, all PRE_FIRST_LIVE status markers unsatisfied. The existing P24-WO 43 unit tests and other workflows must continue to pass. No source or policy in the original WO laboratory is modified.

## Scope, certification and review boundary

**These remain unchanged and barred:** PRE_FIRST_LIVE 0/9 SATISFIED, P24-B BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES, first-Live Owner Human Gate NOT_GRANTED, G13 NOT_STARTED, LIVE_TRADING and AUTO_TRADING DISABLED. S2 broker order lifecycle, operational independent A5 risk veto and production Kill Switch are not tested or certified by this S0 code.

PR must contain only five allowlisted paths: task JSON, standalone S0 Python module, standalone S0 tests, this document and Task Catalog index. The original lab source/test, production config, risk and execution modules, account/credentials, workflow and frozen roadmap cannot change. Owner must grant an independent specific HEAD+Governance Artifact Human Gate for merge; only after postmerge Governance and Branch Hygiene success may this **offline S0 reference implementation** be recorded as code-merged. No live-readiness control may be marked satisfied.

Rollback: revert these five files only; retains all original WO laboratory behavior and safety gating.

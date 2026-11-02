# P24-B — PRE_FIRST_LIVE evidence and unblocking register (preparation ONLY)

**Task:** `FIN-P24-WA-001-R01`; **authority:** documentation/evidence preparation only, NOT P24-B startup.  
**Canonical current source:** `main` @ `26f8072dda23c6f5fefb1edd568ad02c149d4bc1`; `docs/19-production/P24-A-PRODUCTION-READINESS-DOSSIER.md`; `config/production/production-readiness-dossier.json`; [issue #491 Live](https://github.com/rahemih/Finance/issues/491).  
**Status:** P24-A CANONICAL_COMPLETE (`READINESS_ASSESSMENT_ONLY`); **P24-B BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES**; 0/9 PRE_FIRST_LIVE SATISFIED, first-Live Owner approval NOT_GRANTED; 0/3 P24_EXIT; G13 NOT_STARTED; LIVE_TRADING/AUTO_TRADING DISABLED.  
**Scope of this register:** prepare evidence and acceptance gates, **never** amend the production policy, enable broker execution or declare a control PASS.

## Nine authoritative pre-first-Live blockers

All statuses below are `UNSATISFIED` as of this audit. A *draft* or a successful offline CI test cannot flip a status. A5/A8/A10 must independently verify relevant evidence in the actual target production environment.

| # | Canonical ID | Status | Required evidence to change status | Safe next action / accountable gate |
| --- | --- | --- | --- | --- |
| 1 | `OWNER_JURISDICTION_RESOLVED` | UNSATISFIED | Owner-attested actual residence and customer classification, legal/eligibility assessment for applicable licensed venue/data products; jurisdiction is not inferred from IP/location or prior discussion | Owner attests jurisdiction privately; authorized independent compliance review; no personal identification in GitHub |
| 2 | `PRODUCTION_PROVIDER_SELECTED` | UNSATISFIED | Signed/accepted data feed license and entitlements, allowed API/retention/redistribution, timestamps, quality/SLO, fallback and costs for target markets | Research a shortlist AFTER jurisdiction and data rights evidence; do not appoint provider in this document |
| 3 | `PRODUCTION_VENUE_SELECTED` | UNSATISFIED | Eligible broker/exchange entity and account type, documented product/market permissions, order semantics, custody/withdrawal, leverage/risk, limits, legal eligibility and costs | Compare candidates with independent compliance review; MT5 Demo presence is NOT production venue selection |
| 4 | `PRODUCTION_CREDENTIALS_READY` | UNSATISFIED | Human-managed verified KYC/contract/account and segregated vault-backed scoped credentials, funding path evidenced WITHOUT putting keys/funds/account numbers in repo | Owner-only private KYC/funding review, security attestations only; never create or use production credentials autonomously |
| 5 | `PRODUCTION_BROKER_CERTIFIED` | UNSATISFIED | Broker-approved sandbox/integration tests for lifecycle, partial fills, reject/cancel/replace, unknown ACK/idempotency, reconnect and reconciliation with reproducible environment-bound logs | Write contract and test matrix in a later separately governed task, no orders under this register |
| 6 | `UPSTREAM_GATE_FRESHNESS_FOR_LIVE` | UNSATISFIED | A0/A10 revalidate G0..G12 against *selected live* provider/venue, actual policy/data/model versions, source rights, drift and incidents with expiry triggers | Baseline G0..G12 only; no carry-forward PASS claim from research environments |
| 7 | `PRODUCTION_SECURITY_POSTURE_VERIFIED` | UNSATISFIED | A8 independent environment-bound MFA/RBAC/secrets/rotation/egress/tenant isolation/alerts/incident/recovery review | Prepare checklist, freeze secrets in vault; no credentials in PR/issues |
| 8 | `PRODUCTION_RISK_BUDGET_DEFINED` | UNSATISFIED | Owner-specified currency, absolute loss/exposure limits, leverage ceiling, sizing, caps, failure stops and explicit acceptance; A5 independently enforces veto | Request specific budget from Owner only when live context is eligible; never infer amounts from research scenarios |
| 9 | `PRE_LIVE_KILL_SWITCH_VALIDATED` | UNSATISFIED | A5/A6/A8/A9 independently sign off non-real-capital emergency halt + disable-new-orders + replay/reconciliation + recovery under tested target transport | Design safe simulation and broker-sanctioned sandbox drills; offline mock tests do NOT satisfy production control |

### Evidence acceptance schema (mandatory for each of nine)
Each future row may change to `SATISFIED` only after a **separate** approved workstream provides: `environment_id`, `provider/venue name & permitted jurisdiction`, `policy/code versions`, `Owner/authorized reviewer`, `independent A5/A8/A10 review as applicable`, `run/test ID`, `timestamp/expiry`, `integrity digest`, `objective pass/fail`, `redacted link`, `invalidation/recheck triggers`. Empty, stale, synthetic, self-attested, unauthorized or unlicensed evidence => `UNSATISFIED`. Never record secrets, ID documents, demo account numbers or raw system paths.

### Separate gates, to avoid circularity
- `FIRST_LIVE_OWNER_APPROVAL`: **not granted**. Required after (not before) all nine independently certified pre-first-Live controls. Prior project phase authorization, PR merge approvals and this request do not replace it.
- `P24_EXIT`: `LIVE_EXECUTION_VALIDATED`, `P24_G_KILL_SWITCH_DRILLS_COMPLETE`, `G13_OWNER_LIVE_APPROVAL` **all NOT_STARTED/UNSATISFIED**; these are *after* legitimate entry into P24-B and are not new prerequisites for entering P24-B.
- Entry predicate: `p24_b_ready = all_9_verified_in_target_environment AND distinct_FIRST_LIVE_OWNER_APPROVAL`; else `BLOCKED`. The predicate is evaluated in protected, separately governed production-policy task; **this document cannot mutate it**.
- If all nine pass, the *separate* human approval may authorize a **bounded, controlled manual-Live** path only if that approval actually specifies permissible scope; Auto remains disabled. G13 remains a later exit gate. Never auto-enable Live from this doc or CI.

## Existing **read-only DEMO** observations: useful but not production readiness
[Demo evidence tracker #508](https://github.com/rahemih/Finance/issues/508): two independent MT5 Demo terminals, Monday 2026-11-02 60-second sequential and parallel runs; Forex 4/4 instruments and Crypto 7/7 instruments each progressed 30 local samples; `both_demo_identity=PASS`, independent data folders PASS, local pure checks 16/16 PASS; **zero orders sent by the diagnostic**. These facts demonstrate only local read-only data collection, not broker production certification, fund safety, broker API credentials or a deployed A5 Kill Switch.

**Blocking clock defect:** timestamp `time_msc/1000` interpreted as Unix/UTC is approximately **+7202 seconds** relative to current OS UTC on BOTH servers. Windows NTP cross-check measured approximately +2 seconds, not +2 hours, and Windows Time service was STOPPED without administrator privileges. Broker-provided time-zone basis/epoch conversion is **NOT ATTESTED**. Do not silently subtract two hours or treat data freshness as verified for live; keep risk/freshness fail-closed. Next local proof is read-only MQL5 `TimeCurrent()`/`TimeGMT()`/`SymbolInfoTick()` comparison against Python raw epoch under separately reviewed logging, plus eligible provider documentation.

**Still not observed/certified:** real disconnect-reconnect-to-new-tick, broker-attested UTC time, unknown ACK/idempotency, broker-approved sandbox order lifecycle, independent operational risk veto and live-capable Kill Switch. These gaps remain open in #508 and #491.

## Prioritized non-operational work
1. **Evidence intake and Owner attestations:** confirm applicable jurisdiction and target product/markets privately; without owner authority, no production venue/provider can be accepted. Obtain actual written data rights and contractual eligibility before selection.
2. **Clock/data quality:** preserve UTC raw evidence, NTP offset, and both terminals' read-only observations. Document broker/MT5 time interpretation from authoritative permitted source, then repeat controlled no-order tests.
3. **Broker + safety certification plan:** draft exact sandbox state transitions including missing ACK, duplicate/reorder, disconnect/reconnect, risk veto precedence and fail-closed statuses. Test only after A5/A8/A10 review and separate Owner gate.
4. **Production security/risk:** A8 may prepare control matrix, A5 may prepare budget template; monetary caps and account credentials require Owner's explicit choices and evidence.
5. **Freshness reevaluation:** when venue/provider and security/risk are independently accepted, A10 reevaluates G0..G12 in the actual target environment and publishes reviewed artifact.
6. **Gate reconciliation:** Only an individually Owner-approved policy/state PR plus verified postmerge CI can move any blocker to SATISFIED. The separate first-Live Owner decision is non-delegable.

## Status, lineage, and rollback
- This document, its Task Contract and a single Task Catalog entry constitute **evidence-planning only**. No production-policy changes, runtime execution code, external service, credentials, live orders or deployment.
- Any related Github/Linear updates must explicitly say `0/9`, `P24-B BLOCKED`, `G13 NOT_STARTED`, Live/Auto `DISABLED`; no Task Catalog entry or document can claim `READY_FOR_MANUAL_LIVE`.
- Task catalog parent `FIN-P24-WA-001` remains `CANONICAL_COMPLETE`; this follow-up `FIN-P24-WA-001-R01` has separate latest HEAD+Governance Artifact Owner Gate before squash merge, plus exact-main postmerge Governance/Branch Hygiene and Linear reconciliation. If no gate is granted, close draft and leave `main` unchanged.
- Rollback means revert only this docs-only task contract/register/catalog entry. No changes to the frozen Roadmap, P24-A readiness contract, security/risk or G13.

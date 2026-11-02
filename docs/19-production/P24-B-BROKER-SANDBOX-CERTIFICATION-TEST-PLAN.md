# P24-B — Provider acceptance due diligence & Broker Sandbox certification plan

**Task:** `FIN-P24-WA-001-R03` (documents only). **Prepared 2026-11-02.**  
**Canonicals:** [P24-A readiness dossier](P24-A-PRODUCTION-READINESS-DOSSIER.md), [R01 nine-control register](P24-B-PRE-FIRST-LIVE-UNBLOCK-REGISTER.md), [R02 source research](P24-B-PROVIDER-ELIGIBILITY-AND-DATA-RIGHTS-RESEARCH.md), [Live gate #491](https://github.com/rahemih/Finance/issues/491), [Demo evidence #508](https://github.com/rahemih/Finance/issues/508).

**Status invariant:** `PRE_FIRST_LIVE=0/9`, `P24-B=BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES`, `FIRST_LIVE_OWNER_GATE=NOT_GRANTED`, `G13=NOT_STARTED`, `LIVE_TRADING=DISABLED`, `AUTO_TRADING=DISABLED`. This design is **NOT** proof that any test was run, broker approved, data licensed, jurisdiction established or provider chosen. Full P24 remains ACTIVE.

## 1. First-party source review: who is actually allowed to serve whom?

Public pages are **research evidence, not client-specific acceptance**. The Owner must privately attest actual legal residence, contracting party, intended trading products and account class; an independent compliance reviewer must check applicable rules and entity-specific contract terms. Conditional Iran analysis is a scenario only, not an assertion about an individual or an invitation to evade restrictions.

| Candidate / role | Source and fact checked 2026-11-02 | Missing written evidence / verdict |
| --- | --- | --- |
| LiteFinance Global LLC | [Registered offices](https://www.litefinance.org/company/registered-offices/) distinguishes St. Vincent & Grenadines Global LLC (its page states **Regulator: No**) from separate Mauritius and Cyprus entities with distinct protections. [Legal documents](https://www.litefinance.org/company/documents/) are company-specific; the public page does not grant eligibility. | `UNKNOWN / NOT_SELECTED`: identify *actual* legal contracting entity, resident/client/product exclusions, current agreement, licensed permitted use, operational broker API/sandbox, incident/withdrawal rights. Regulatory protection of one entity may not be attributed to another. |
| FIBO Group Ltd | [FIBO regulation](https://www.fibogroup.com/about/licences/) publicly states BVI FSC licence SIBA/L/13/1063. Its [documents](https://www.fibogroup.com/documents/) include customer agreement, KYC, **client acceptance policy** and a longer restricted-jurisdiction list; sample country exclusions are not exhaustive. | `UNKNOWN / NOT_SELECTED`: read *full* client acceptance/contract effective for actual entity and current residence, accepted client class/products, broker-approved sandbox and account API. BVI status ≠ acceptance of any given client. |
| MetaTrader 5 / MetaQuotes-Demo | [MT5 account help](https://www.metatrader5.com/en/terminal/help/startworking/acc_open) distinguishes virtual Demo from broker-managed Real accounts; [MT5 account authorization](https://www.metatrader5.com/en/terminal/help/startworking/authorization) explains Investor password is read-only and Master enables trading. | `DEMO_ONLY / NO_PRODUCTION_VENUE`: two connected local Demo terminals are only read-only observations. Do not request or store either type of password in GitHub/Linear. |
| Market-data permissions | [Twelve Data terms §2.2](https://twelvedata.com/terms) allow **non-display** only as enabled by the subscribed tier, and external display/redistribution only with add-on or written agreement. [TradingView Terms §3](https://www.tradingview.com/policies/) explicitly prohibit ordinary feed usage for non-display algorithmic decision, execution or machine risk control. | `NOT_LICENSED_FOR_PRODUCTION`: written vendor/data-originator authorization for the exact instruments, 10 internal users, display/non-display, algo/risk use, storage/retention, derived data, redistribution, UTC provenance, SLO and jurisdiction. Do not use restricted sources as automation inputs. |

**Decision table for each company/entity (not supplied by ordinary public marketing):** legal entity/registration and regulator checked independently; permitted actual residence; KYC/identity requirements; allowed product list/derivatives class; margin/leverage and risk disclosure; eligible order transport/API; separate sandbox terms; accounts and credentials stewardship; approved automation status; fees, custody and withdrawal; enforceable data entitlement; UTC timestamp/clock basis; outage handling; account shutdown/reconciliation; incident/security contact; current dated source URL; named independent legal/risk/security approval; validity horizon and invalidation trigger.

A provider verdict can only be `ELIGIBLE_VERIFIED` after written, independently reviewed evidence for the actual client and product; otherwise `UNKNOWN` or `EXCLUDED`. **No venue/provider has been selected** here.

## 2. Trust boundary & phases of test authority

| Level | Environment | Allowed now? | What can be claimed |
| --- | --- | --- | --- |
| **S0 — Deterministic isolated simulator** | Local synthetic fixture; no MT5 connection or network mutation | YES in a separately approved development workstream; this document only specifies cases | Contract coverage and isolated fail-closed logic, NOT broker certification |
| **S1 — Broker Demo READ-ONLY** | Two independent local MT5 terminals; query account/terminal/symbol/tick/position only | Existing read-only diagnostic observations available; new runs require Owner-local execution | Identity, advancing prices, status, read-only reconnect observation only |
| **S2 — Broker-sanctioned order Sandbox** | Explicitly eligible/contractually permitted test account, transport and test orders | **NO. Requires new separate Owner Human Gate**, A5/A8/A10 review, broker rights, approved risk policy and scope | Only after actual signed logs, certified order/ACK/partial-fill/reconcile tests; never from S0/S1 |
| **S3 — Real-money Manual Live** | Production account with funds | **NO, out of scope; P24-B BLOCKED** | Cannot start until all nine PRE_FIRST_LIVE controls and distinct FIRST_LIVE_OWNER_GATE pass |

Important API distinction: [MT5 `order_check`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercheck_py) checks request/funds but **does not execute or guarantee execution**; [MT5 `order_send`](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py) sends an actual trading request to the server. Neither shall be called by this plan. A sandbox future action must be explicitly scoped, never assumed safe because the account label says Demo.

## 3. Sandbox certification matrix — specifications, NOT executed results

For S0, use deterministic stubs with no broker connection. For S1, passive terminal observation only. S2 scenarios are **DESIGNED / NOT AUTHORIZED / NOT TESTED** until independent gates are satisfied; never fabricate retcodes or broker ACKs.

| Test ID | Level | Required stimulus / observation | Expected PASS + safe response |
| --- | --- | --- | --- |
| **SC-01** | S0/S1 | Two independent configured terminal paths with disjoint data directories | Both expected Demo IDs and server labels present, no cross-routing; missing/mismatched => REJECT |
| **SC-02** | S0/S1 | Read-only 11-symbol tick progress on both accounts | Per-symbol timestamp/quote sanity tracked; stale/missing => QUARANTINE, no trading permit |
| **SC-03** | S0/S1 | Raw `time_msc` compared to UTC OS, NTP, native MQL5 source | Offset and source semantics independently attested; current ~+7202s => `UNVERIFIED_TIME`, no normalization, fail-closed |
| **SC-04** | S0 | Disconnected terminal before candidate order | A5-independent pre-trade firewall returns veto; no order request produced |
| **SC-05** | S0/S1 | Passive connection transitions connected → disconnected → recovered | S1 may mark `RECOVERY_OBSERVED` only on real down/up plus later fresh tick; otherwise `NOT_OBSERVED`; never cause a physical disconnect here |
| **SC-06** | S0 | Corrupt/missing tick timestamp or wrong symbol/venue | `DATA_QUARANTINE` and veto, no age/latency calculation on untrusted epochs |
| **SC-07** | S0 | Cross-market account mismatch (Crypto symbol routed to Forex) | Rejected independently of strategy output, no order call |
| **SC-08** | S0 | Owner Gate not granted / venue not certified / source licence absent | Veto takes precedence over all signals; recorded reason |
| **SC-09** | S0 | Risk budget absent or ceiling exceeded / leverage breach | Independent A5 veto, no synthetic order emitted |
| **SC-10** | S0 | Kill Switch active before request | All **new** synthetic submissions blocked, existing state preserved for reconciliation |
| **SC-11** | S0 | Duplicate client intent/idempotency key | Deterministic dedupe prevents duplicate order intent; immutable audit record |
| **SC-12** | S0 | Request sent, ACK missing / timeout | `UNKNOWN_OUTCOME`; **never blindly retry**; query authoritative order/deal state before any reattempt |
| **SC-13** | S0 | Late ACK after timeout / message reorder | Reconcile to one final state, no duplicate-fill assumption, audit timestamps |
| **SC-14** | S0 | Partial fill then reject / remainder pending | Position/exposure computed from verified fills only; remainder handled under policy, no invented complete fill |
| **SC-15** | S0 | Server reject: price, volume, margin, market closed | Reject stays terminal, no undirected retry; risk controls remain active |
| **SC-16** | S0 | Cancel/replace race with fill | Explicit `CANCEL_PENDING`/unknown state until authoritative broker reconciliation; never treat cancellation request as cancellation success |
| **SC-17** | S0 | Disconnect after order accepted, before reconciliation | Enter fail-closed recovery; query authoritative order/position/deal snapshot before enabling new intents |
| **SC-18** | S0 | Emergency halt while multiple intents queued | No new intents accepted; previously sent simulated intents reconciled before subsequent activity |
| **SC-19** | S0 | Reconnect to a different server/account/entity | Hard identity veto, no release until exact expected environment attestation |
| **SC-20** | S0 | Audit log tampering or missing evidence hash | A10 marks certification INVALID/FAIL; independent A8 review required |
| **SC-21** | S0 | Provider quote licence expires/changes mid-session | Immediately suspend dependent price features; no silent fallback to TradingView/non-display prohibited source |
| **SC-22** | S2 ONLY | Broker-sanctioned test order lifecycle, partial fills, cancel/replace, rejects, ACK, replay | **NOT_RUN**; must have separately approved exact venue/order contract, live broker sandbox receipts, A5/A8/A10 independent reviews |
| **SC-23** | S2 ONLY | Broker-sanctioned non-funds emergency Kill Switch drill | **NOT_RUN**; A5/A6/A8/A9 independent evidence required, no production or real funds |
| **SC-24** | S2 ONLY | Broker time-zone and order/quote time-source certification | **NOT_RUN**; independent provider-stated UTC/epoch semantics required with time-synchronized receipts |

**Gate severity:** Any SC-03/04/06/08/09/10/12/16/17/19/20/21 failed or unknown => `FAIL_CLOSED`. A local simulator `PASS` for any case has no authority to change P24-B `PRE_FIRST_LIVE` status or production trading permissions.

## 4. Evidence contract and objective acceptance

For each future actual S1/S2 test, evidence must include redacted unique test ID and test version, test tier, provider/venue legal entity and exact environment, symbol/time basis, connected server (non-sensitive identifier only), policy/hash, A5 and A8 reviewer identity attested **outside** the public repo, A10 digest, signed order/transport request+response when legally authorized, complete state transition, expected/actual values, timestamps with timezone provenance, accepted/fail-closed result, run timestamp, expiry/incident invalidation and immutable link. **NEVER** publish account numbers, authentication details, KYC, full Windows terminal paths, real prices that violate data contracts or funded-account artifacts.

**DoR for S2:** Written broker permission for exact legally eligible sandbox + authorized order API, distinct Owner gate for testing (and risk budget), A5/A8/A10 approvals, separate credential vault and secrets non-disclosure, test design containing safety/rollback/outage handling. Missing any means **S2 NOT_AUTHORIZED**.

**DoD for `PRODUCTION_BROKER_CERTIFIED`:** Actual eligible venue demonstrated in governed separately approved environment; all required S2 scenarios independently passed with accepted, unexpired, signed and reproducible evidence; reconciliation/unknown outcomes and security verified. Until then `PRODUCTION_BROKER_CERTIFIED=false`.

**DoD for `PRE_LIVE_KILL_SWITCH_VALIDATED`:** Operational target transport safety proved and signed by A5/A6/A8/A9, no assumption from existing synthetic Kill Switch; until then `false`.

All nine PRE_FIRST_LIVE entries remain false, and no P24-B start or first-Live owner approval occurs under this document.

## 5. Follow-up checkpoints and rollback

1. **S0 specification review:** audit this 24-case matrix for missing states, test oracles, false-pass failure modes and A5/A8/A10 independent reviewer requirements; implementation can follow in its own approved workstream.
2. **S1 source-clock proof:** compare Python raw MT5 `time_msc` with native MQL5 `SymbolInfoTick()`, `TimeCurrent()`, `TimeTradeServer()`, `TimeGMT()` and independent NTP; do not modify timestamps or network settings. Preserve existing unverified offset around 7202s.
3. **Venue feasibility and rights:** obtain vendor's specific written eligibility and account/sandbox/API/data rights **only after actual private Owner jurisdiction attestation**. Do not bypass restrictions.
4. **S2 separate contract:** create new scope-specific task and Human Gate; no simulated A5 veto can certify the real Kill Switch. Do not execute orders or tests while this remains blocked.
5. **Readiness reevaluation:** only when all nine individually attested controls plus separate first-Live Owner gate are satisfied, consider P24-B entry. G13 remains a later P24 exit criterion.

**This PR change set:** contract `FIN-P24-WA-001-R03.json`, this document and a Task Catalog index only. Do not alter config/production, G13, runtime, GitHub workflows, secrets, Live/Auto or frozen roadmap. Owner exact-HEAD + Governance Artifact approval, merge and postmerge CI are necessary only to promote **this planning document**, not any broker certification or operational P24 status. Revert only these three paths if invalidated.

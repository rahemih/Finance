# P24-B — Formal Owner decision and licensed dual-source market-data acceptance plan

**Task:** `FIN-P24-WU-001` • **Review date:** 2026-11-07 • **Record class:** `OWNER_ARCHITECTURE_APPROVED / RIGHTS_AND_QUALITY_UNCERTIFIED`  
**Authority:** document research, not data ingestion or provider contract.  
**Non-negotiable:** `PRE_FIRST_LIVE = 0/9`; `PRODUCTION_PROVIDER_SELECTED.satisfied=false`; P24-B blocked, G13 NOT_STARTED, Live/Auto disabled. A5, A8, A10 retain veto/evidence and no trading access is authorized.

## 1. Owner-APPROVED architecture (definitive selection of architecture)

The Owner approved the following without limitation of their own comprehensive technical/legal evaluation:

| Product family | Owner-approved primary | Independent reference required | Status of source licence |
| --- | --- | --- | --- |
| FX currency pairs + metals + energy CFDs | **xChief** broker's **MetaTrader 5** quotes, **from its own authorised target server** | Separate licensed FX/commodity price feed | **Source implementation and actual broker data-use rights NOT attested** |
| Crypto spot | **Toobit** market-data REST / WebSocket | Independent licensed venue-aware crypto source; aggregate reference optional | **Source implementation and actual automated/non-display rights NOT attested** |
| Crypto perpetual contracts and any explicitly supported dated contracts | **Toobit** contract-specific API market data | A separately licensed **contract/product-aware** futures reference if available; no substitute with generic BTC spot | **Product-specific rights and exact contract support NOT attested** |

Do not substitute historical LiteFinance/MetaQuotes Demo feeds for xChief's target server. Do not assume that generic MT5 CFD crypto symbols represent spot assets or exchange-delivered futures. The Owner does not need to choose a broker/exchange again. A later provider failure leads to recorded exception/Owner change approval, not silent re-selection.

## 2. First-party source evidence and permission boundaries

| Role / candidate | Public evidence inspected, as of 2026-11-07 | What is sufficiently established | What is NOT established (no production licence PASS) |
| --- | --- | --- | --- |
| **xChief MT5** primary FX and commodities | [Official MT5 platform](https://www.xchief.com/platforms/metatrader5/), [xChief account types](https://www.xchief.com/trading-conditions/account-types/), [official MetaTrader5 Python interface](https://www.mql5.com/en/docs/python_metatrader5) | MT5 platform handles quotes, bid/ask/spread; account classes advertise FX, metals and commodity CFDs; MQL5/MT5 provides a technical path to read ticks and bars | Actual price feed terms for non-display machine signals and risk gating; automated/derived data rights, attribution, raw-history retention, 10 internal users, source clock convention, effective legal entity/region, data costs and uptime. **MT5 technical API alone cannot grant broker market-data rights** |
| **Toobit** primary crypto | [Spot data](https://api-docs.toobit.com/api/spot-market-data), [USDT-M data](https://api-docs.toobit.com/api/usdt-m-market-data), [spot WebSocket](https://api-docs.toobit.com/api/spot-websocket-market-data), [API basic info](https://api-docs.toobit.com/api/basic-information.html), [Toobit Terms effective 2025-08-01, posted 2026-06-22](https://www.toobit.com/en-US/support/terms-of-service) | REST server time, symbol metadata, klines and quotes plus WS streaming. Terms §16.1 reserve written permission for further material distribution; §16.3 disclaims guaranteed accuracy, completeness and freshness. HTTP429 backoff and not trusting potentially removed `rateLimits` exchangeInfo field are documented | Client-specific and instrument-specific entitlement, commercial/private algorithmic non-display, 10-seat internal sharing, derived model training use, retention, licence to store reference quotes, geography and API permission. API documentation does not equal an unrestricted data licence |
| **Twelve Data** secondary FX/commodity **priority for contract review** | [Terms updated 2026-01-01](https://twelvedata.com/terms), [Commercial vs personal plan guidance](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage), [Attribution guidance](https://support.twelvedata.com/en/articles/12647398-attribution-guidelines-for-using-twelve-data) | The terms define authorised users, internal use, `Non-Display Use`, subscription tier, retention and third-party data rights. Individual Pro guidance includes programmatic internal AI assistants; business plans can allow commercial/internal usage subject to exchange/region rules. Internal risk analytics may not require public attribution under applicable licence | A specific plan **and signed entitlement** for target FX/commodity symbols (especially gold/silver, oil and natural gas), permitted non-display A5 risk signals, 10 internal users, broker-vs-reference quote comparison, market-data vendor and country eligibility, retention, geographic/commercial add-ons and SLO. Do **not** assume personal tier covers a business/10-user production platform |
| **CoinAPI** secondary crypto **priority for contract review** | [Official data usage policy](https://www.coinapi.io/usage-policy) | Official guidance describes internal quantitative trading, analytics, ML and risk management as generally internal use; customer-facing raw data and resale need a separate redistribution agreement | Exact Toobit-like spot/perpetual coverage and liquidity, product/venue semantics, reference independence, region/service eligibility, historical rights, number of seats, rate quotas, contract, cost and legally binding Customer Agreement still to be confirmed |
| **CoinGecko** *tertiary context-only* crypto aggregate | [License FAQ updated 2026-10-19](https://support.coingecko.com/articles/1043089972-what-are-the-differences-between-commercial-and-custom-licenses), [API pricing](https://www.coingecko.com/en/api/pricing) | Paid plans explicitly describe personal/internal analytics and some commercial display with attribution; no default redistribution, sublicensing or white-label. Free Demo plan **does not** carry commercial rights; retention limits and termination deletion conditions apply | NOT a contract-matched Toobit/perpetual reference and not for exchange-specific execution-price equality checks; exact plan, attribution, retained data, 10-seat rights, AI model training restrictions, region and payment eligibility unverified |

**Important source licence interpretation:** Under Twelve Data's own terms, internal, non-display and redistributed usage categories carry different rights. CoinAPI's informational usage page itself points to a separate binding Customer Agreement. CoinGecko's standard commercial plans do **not** grant unrestricted redistribution, and their 2026 FAQ says AI model training is NOT included in ordinary plans. This research is **not** a signed licence or legal opinion; written provider acceptance and independent assessment are prerequisite to production.

## 3. Proposed reference hierarchy and selection logic

- **FX:** xChief MT5 remains sole *venue execution-price authority*; independent Twelve Data is a reference for detecting anomalies and source drift, not a price guaranteed to equal xChief's CFD quote.
- **Crypto spot:** Toobit spot bid/ask/last and trades are primary. CoinAPI venue-paired spot comparison is a first priority **only if both same pair and quote currency are covered with independent source provenance**. CoinGecko aggregate reference is an outlier detector for indicative BTC/ETH and large-cap prices, *not* an order-level benchmark.
- **Crypto derivatives:** Match Toobit product identifier, venue, underlying, settlement currency, expiration/perpetuity, margin/index/mark/last basis, funding interval, quote currency and contract multiplier. **Never compare perp mark/index to aggregate spot with a hard universal equality threshold.** If reference coverage is missing, label unsupported; do not invent a reliable comparator.
- **No single-source auto-fallback**: an independent licensed reference can flag anomaly, not authorize switching broker or exchange execution price feed. Market source failures should disable affected signals and new trade eligibility by A5 veto.
- **Cost:** zero providers purchased; no price/availability promise; compare a full 10-user internal licence and target rate/WS quota before selecting a paid plan. Confirm residency, billing and export restrictions without bypass.
- **FA inputs:** FX/crypto fundamental/news feeds may require separate licences and must not be disguised as numeric quote data rights; beyond this market-data subtask.

## 4. Objective quality and safety acceptance matrix

Each real feed must carry `source_id, legal_entity, licence_id+entitlement_scope, effective_from/to, reviewer, contract_version, venue+product_id, symbol, quote_currency, bid, ask, last, event_time_raw, event_time_source_clock, receive_time_utc, normalized_utc, timestamp_confidence, quote_type, origin, transport, quality, gap_seq, SHA256_evidence` with sensitive tokens redacted.

| Test | Proposed input / expected safe result | Acceptance evidence |
| --- | --- | --- |
| Source and subscription | Verify signed agreement from each vendor for intended region, 10 users, analytics/non-display, retention, AI use and independent prices | Contract version, explicit rights matrix, A8/A10 signed check and expiry |
| Time / server offset | Compare original tick timestamp to UTC clock, server-time endpoint where present, distinct send/receive time and any DST/timezone conversion | Raw broker tick, UTC reference, signed clock-semantics note; **do not assume prior MT5 Demo +7202s is a universal correction** |
| Market coverage | Confirm exact symbols for EUR/USD, gold/silver, oil/gas, BTC/ETH/selected alts; validate Toobit spot/perpetual metadata and contract status | Exact entitlement map by instrument/product, source plan/venue |
| Price meaning | Isolate CFD vs spot and last/bid/ask/mid/mark/index; no inappropriate price equality comparisons | Pair and quote type conversion provenance with defined tolerance by asset/session, A5 reviewed |
| Freshness and sequence | Inject intentionally stale, delayed, missing, reordered, duplicate timestamps and connection break; reject invalid data | Test payloads + repeatable logs; limit chosen using actual latency samples, **not invented global milliseconds** |
| Feed disagreement | Simulate crossed books, widening spreads, outliers and conflicting references; block new affected strategies/orders until reviewed | Per-symbol thresholds with statistically valid calibration and A5 veto |
| Availability and repair | Inject 429/5xx throttling, WS ping/pong loss, reconnect gaps, symbol suspended, FX weekends and market closed | Exponential backoff with provider guidance, snapshot resync, fail-closed no-order proof |
| Security | No write-trade keys for read-only ingestion, least privilege, IP allowlist where supported, token rotation and egress restrictions | Vault-backed redacted evidence and A8 independent decision |
| Retention / expiration | Simulate licence expiry, vendor ToS change, share-limit breach, termination deletion and no redistribution | A10 source-lineage and expiry register, purge/disable test |
| Operational qualification | Broker-sanctioned Demo and reference feed operation in separate lawful target environment only after written permission | Independent reviewer, exact environment, source/product IDs, timestamps, replay determinism and integrity hashes |

**A5 safety rule:** missing/unauthorised source licence; unknown quote timestamp semantics; stale/missing/conflicting market data; rate-limit exhaustion or fallback ambiguity => `NO_NEW_ORDERS / SIGNAL_INVALID` for affected instruments. No action is authorised by this document. Actual controls require separate governed engineering implementation and independently verified tests before claiming deployed pass.

## 5. Missing approvals — explicit conclusion

- [x] Owner architecture decision complete: xChief/MT5 + Toobit/API primaries + independent licensed references.
- [x] First-party technical and licensing source shortlist reviewed; Twelve Data + CoinAPI are *preferred secondary research targets*, CoinGecko *tertiary context only*.
- [ ] xChief official market-data/non-display contract and server timestamp rights; Toobit API terms and actual permission for ten internal users, automated internal risk processing and storage.
- [ ] Twelve Data / CoinAPI (and optional CoinGecko) actual suitable commercial and internal non-display agreements, authorised region and fees.
- [ ] Independent source-bound A5/A8/A10 qualification with at least the tests above; no provider account created, keys read or live data fetched in this research package.
- [ ] Exact policy-compliant change of `PRODUCTION_PROVIDER_SELECTED.satisfied` from `false` only **after** the separately governed required proof; do not unilaterally flip it.

**Overall:** `OWNER_ARCHITECTURE_APPROVED`, `DATA_RIGHTS_AND_OPERATIONAL_EVIDENCE_BLOCKED`, formal `PRODUCTION_PROVIDER_SELECTED = UNSATISFIED`. All 9 `PRE_FIRST_LIVE` controls still `false`, P24-B blocked and Live/Auto disabled. PR #524 and #525 remain their own unmerged gated tasks. This package adds **only** documentation, Task Contract and Task Catalog; a separate exact-head Owner merge Human Gate with postmerge CI/Branch Hygiene remains mandatory.

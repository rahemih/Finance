# P01-E — Cost / Licensing / Data Rights

Task: `FIN-P01-WE-001`  
Linear: `HOS-117`  
Assessed: 2026-10-03  
State: RESEARCH_BASELINE / NO_PRODUCTION_SELECTION

## Purpose

This artifact records public pricing, licensing/data-rights boundaries, quote-required gaps and scenario-cost formulas for the P01-B market-data candidates and P01-C execution candidates.

It does **not** purchase services, accept terms, infer the Owner's professional/non-professional status, select a production provider, create credentials/accounts, or enable any trading mode.

## Research rules

- Numeric prices are recorded only when publicly documented by an official source as of the assessment date.
- Unpublished or contract-specific pricing is `QUOTE_REQUIRED`.
- Rights that depend on the intended use, exchange/index, client class or contract are `CONTRACT_REVIEW`.
- Technical API access does not imply redistribution, non-display, automated-analysis or production rights.
- Market-data licensing is separate from trading authorization.
- All time-sensitive pricing must be revalidated before procurement or later production use.

## Market-data provider cost baseline

| Provider | Public pricing baseline | Rights / licensing state | P01-E disposition |
|---|---|---|---|
| Databento | Standard $199/mo; Plus $1,750/mo; Unlimited $4,500/mo; usage-based historical pricing also exists | venue/use-specific licensing and entitlements; external distribution is plan/right dependent | PUBLIC_PRICE_WITH_LICENSE_DEPENDENCIES |
| dxFeed | No canonical public production quote established | commercial quote, source entitlements and usage rights require contract review | QUOTE_REQUIRED |
| Twelve Data | Individual: Basic $0, Grow $79, Pro $229, Ultra $999/mo. Business page shows Venture/Enterprise/Enterprise+ with business-use rights and dynamic pricing | personal/internal vs business/external rights are plan-dependent; redistribution requires separate rights/agreement; exchange add-ons can apply | PUBLIC_PRICE_WITH_USAGE_RIGHTS_BOUNDARIES |
| Massive | Currencies Basic $0, Starter $49/mo; Indices Basic $0, Starter $49/mo, Advanced $99/mo | business/commercial rights and dataset entitlements require plan/contract review | PUBLIC_INDIVIDUAL_PRICE_BUSINESS_REVIEW_REQUIRED |
| Kaiko | custom enterprise quote | standard license and exchange agreements; exact channels/history/use rights are contract-specific | QUOTE_REQUIRED |
| CoinAPI | Startup $79/mo, Streamer $249/mo, Pro $599/mo, Enterprise custom; metered option available | redistribution/non-display/retention and other production rights require contract review | PUBLIC_PRICE_RIGHTS_REVIEW_REQUIRED |
| FRED / ALFRED | no public subscription fee identified for normal API access | series-level copyright/use restrictions remain; third-party series rights are not overridden by FRED access | SERIES_BY_SERIES_RIGHTS_REVIEW |
| Direct official sources | source-specific | exchange/index/agency-specific | SOURCE_SPECIFIC_REVIEW |
| Blockscout | instance/deployment-specific | API/instance-specific; supplemental on-chain source only | PRODUCTION_SOURCE_DEFERRED |

### Important public-rights observations

**Databento:** public pricing supports usage-based and subscription models. Its licensing portal states venue license fees are assessed by venues and can be passed through. Exact non-display/display/distribution rights depend on dataset and use case.

**Twelve Data:** individual plans are for personal/internal use; business plans cover commercial/internal/external usage subject to exchange licensing. Redistribution is not automatically granted by an individual plan and can require a separate agreement or rights add-on.

**Kaiko:** public material says enterprise pricing is custom based on assets, instruments, data type, granularity, live/history and usage. A standard licensing agreement exists, but the intended production use must still be checked against the applicable contract.

**FRED/ALFRED:** availability through the API does not remove third-party copyright restrictions. Rights must be checked for the selected series.

## Execution-cost baseline

| Venue | Public cost evidence | P01-E handling |
|---|---|---|
| Coinbase Advanced | maker/taker fees vary by product and signed-in account fee tier | ACCOUNT_TIER_DEPENDENT; exact numeric rate remains unresolved |
| Kraken | current public 2026 entry tier shows 0.40% maker / 0.80% taker, with lower tiers based on volume or assets-on-platform | public baseline only; revalidate at execution time |
| Binance | regular spot public schedule shows 0.10% maker / 0.10% taker; BNB-discount example 0.075% / 0.075% | pair/promotion/VIP/jurisdiction dependent |
| OANDA v20 candidate | US public core pricing: $0.70 per 10,000 units per leg; spread-only model also exists | entity/region/account specific; revalidate eligible contracting entity |
| IBKR | public spot-FX Tier I: 0.20 basis point × trade value, minimum $2/order | account/program and market-data subscriptions are separate |
| Saxo OpenAPI candidate | spread/tier/country-dependent; exact pricing is available in platform trade tickets; rollover/financing applies where relevant | REGION_AND_TIER_DEPENDENT |

## Data-rights dimensions

Every candidate must be evaluated separately for:

1. internal display;
2. internal non-display;
3. automated analysis;
4. algorithmic use;
5. storage;
6. raw retention;
7. derived-data / model-training use;
8. redistribution;
9. exchange or index entitlements;
10. professional / non-professional classification.

A technical endpoint or paid subscription does not by itself prove all ten rights.

## Scenario cost model

The project must use formulas rather than invented totals:

`fixed_data_monthly = SUM(public_plan_fees + quoted_vendor_fees + exchange/index_entitlements + mandatory_support/license_fees)`

`variable_data_monthly = SUM(usage_gb_or_messages × unit_rate + API_overage + data_egress)`

`execution_monthly = SUM(traded_notional × commission_rate + spread_cost + financing/funding + venue_pass_through_costs)`

`operations_monthly = compute + storage + backups + egress + observability + security_tooling`

`total_monthly = fixed_data_monthly + variable_data_monthly + execution_monthly + operations_monthly`

### Scenario A — Research / self-serve

Use publicly available self-serve plans only where the intended internal research use is permitted. No redistribution and no production-provider conclusion.

### Scenario B — Production data candidate

Include enterprise/business subscription, non-display rights, exchange/index entitlements, SLA/support and any quote-required components. A candidate remains unresolved if a required right is still `QUOTE_REQUIRED` or `CONTRACT_REVIEW`.

### Scenario C — Execution evaluation

Use actual account fee tier, spread/slippage distribution, financing/funding, and required market-data entitlements. Jurisdiction and account eligibility remain separate gates.

## Unresolved / Human-Gate items

The following remain intentionally unresolved:

- Owner professional/non-professional classification;
- Owner/account jurisdiction and eligible contracting entity;
- exact exchange/index non-display and redistribution entitlements;
- Kaiko and dxFeed commercial quotes;
- actual Coinbase account fee tier;
- any non-public production SLA/support commitments;
- final infrastructure/storage/egress quantities.

No value above is inferred from user memory.

## P01-F handoff

P01-F may compare primary/backup candidates using this evidence, but it must not select a candidate whose mandatory rights remain unresolved. Jurisdiction/client-class requirements from P01-D must remain attached to every candidate.

## Official source register

- Databento pricing: https://databento.com/pricing
- Databento licensing portal: https://databento.com/docs/portal
- dxFeed coverage: https://dxfeed.com/coverage/global/
- dxFeed terms: https://dxfeed.com/tr/general-terms-and-conditions-for-services/
- Twelve Data individual pricing: https://twelvedata.com/pricing
- Twelve Data business pricing: https://twelvedata.com/pricing-business
- Twelve Data commercial/personal usage: https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage
- Twelve Data terms: https://twelvedata.com/terms
- Massive currencies pricing: https://massive.com/pricing?product=currencies
- Massive indices pricing: https://massive.com/pricing?product=indices
- Kaiko pricing and licensing: https://www.kaiko.com/about-kaiko/pricing-and-contracts
- CoinAPI pricing: https://www.coinapi.io/products/market-data-api/pricing
- CoinAPI docs: https://www.coinapi.io/products/market-data-api/docs
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- FRED terms: https://fred.stlouisfed.org/docs/api/terms_of_use.html
- Coinbase Advanced fees: https://help.coinbase.com/en-gb/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees
- Kraken 2026 fee tiers: https://support.kraken.com/articles/cross-platform-fee-tier-changes
- Binance spot fees: https://www.binance.com/en/fee/trading
- OANDA US pricing: https://www.oanda.com/us-en/trading/our-pricing/
- OANDA core spread + commission: https://help.oanda.com/us/en/faqs/spreads-commission.htm
- IBKR spot currency commissions: https://www.interactivebrokers.com/en/pricing/commissions-spot-currencies.php
- IBKR market-data pricing: https://www.interactivebrokers.com/en/pricing/market-data-pricing.php
- Saxo FX pricing: https://www.home.saxo/rates-and-conditions/forex/spreads-and-commissions
- Saxo general charges: https://www.home.saxo/rates-and-conditions/commissions-charges-and-margin-schedule

## Safety state

Production provider selected: NO  
Production execution venue selected: NO  
Subscription purchase: NONE  
Terms accepted: NONE  
Credentials: NONE  
Accounts/KYC/funding: NONE  
Live Trading: DISABLED  
Auto Trading: DISABLED

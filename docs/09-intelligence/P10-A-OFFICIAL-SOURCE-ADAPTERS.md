# P10-A — Official Source Adapters

Task: `FIN-P10-WA-001`  
Linear: `HOS-233`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P10-WA-001-01` / ACQUIRED  
Lead: A3 Market Intelligence  
Support: A0, A1, A2, A4, A8, A9, A10  
Fresh official-source verification: 2026-10-10

## Objective

Create the official-first ingestion boundary for P10 Fundamental / Macro / Event Intelligence.

P10-A does **not** download production data yet. It defines which official sources are eligible, how they can be accessed, which authentication/licensing constraints apply, and what revision/vintage semantics may safely be claimed.

## Canonical source classes

Each source declares:

- stable source ID and institution;
- access kind: REST API, SDMX API, public download, official portal or licensed portal;
- authentication mode;
- revision/vintage mode;
- official base/documentation URLs and allowed hosts;
- dataset capabilities;
- transport activation state;
- licensing state;
- verification date and caveats.

The registry is deterministic and content-addressed.

## Official-first baseline

### FRED / ALFRED

Official API documentation:  
https://fred.stlouisfed.org/docs/api/fred/

The API exposes series observations, release metadata and vintage dates. ALFRED/FRED real-time periods support historical views. P10-A therefore permits `NATIVE_VINTAGE` semantics for this source.

API key handling is **reference-only** through `secret://` handles. No key is stored in repository state.

### U.S. Bureau of Labor Statistics

Official API:  
https://www.bls.gov/developers/home.htm

BLS documents public v1 access without registration and registered v2 access with higher limits. P10-A does not claim a native historical-vintage API; revisions must be captured by NEXUS QUANT observation/vintage storage when ingested.

### U.S. Bureau of Economic Analysis

Official API:  
https://apps.bea.gov/api/signup/

BEA provides programmatic statistics and metadata and requires registration/API-key handling. P10-A stores only secret-reference semantics.

### CFTC

Official Commitments of Traders source:  
https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

CFTC publishes weekly and historical COT files and a public reporting environment. P10-A models these as publication snapshots, not as a real-time trading feed.

### European Central Bank

Official API overview:  
https://data.ecb.europa.eu/help/api/overview

Official data-query documentation:  
https://data.ecb.europa.eu/help/api/data

ECB provides an SDMX 2.1 RESTful service. Its data API supports `updatedAfter` and `includeHistory=true`, so P10-A explicitly records historical revision retrieval capability.

### Eurostat

Official API documentation:  
https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/

Eurostat provides Statistics and SDMX APIs. Its official API guide states that statistical datasets expose the latest version and do not preserve past statistical dataset versions. Therefore P10-A records `LATEST_ONLY` rather than inventing vintage support.

### Bank of England

Official database/help:  
https://www.bankofengland.co.uk/boeapps/database/help.asp

The IADB database supports automated series downloads and provisional/footnote flags. P10-A does not claim a complete native vintage-history API.

### Bank of Japan

Official API manual:  
https://www.stat-search.boj.or.jp/info/api_manual_en.pdf

The BOJ launched the Time-Series Data Search API on 2026-02-18. It provides JSON/CSV time-series and metadata access. Revisions may occur, but P10-A does not claim a native historical-vintage query unless independently proven later.

### Bank for International Settlements

Official Data Portal developer help:  
https://data.bis.org/help/tools

BIS provides an SDMX RESTful API for data and metadata. Native full vintage-history semantics are not assumed.

### IMF

Official API page:  
https://data.imf.org/en/Resource-Pages/IMF-API

The IMF Data portal documents SDMX 2.1 and SDMX 3.0 APIs. The current Swagger exploration path asks for beta-portal sign-in; therefore P10-A marks transport/auth as `PORTAL_ACCOUNT_OR_REVALIDATION` instead of assuming anonymous production access.

### World Bank

Official Indicators API documentation:  
https://datahelpdesk.worldbank.org/knowledgebase/articles/889392

The World Bank Indicators API v2 requires no API key and exposes nearly 16,000 indicators. P10-A permits offline request specifications but does not claim native vintage history.

### EIA

Official APIv2 documentation:  
https://www.eia.gov/opendata/documentation.php

EIA APIv2 is RESTful and requires an API key. Canonical code accepts only a `secret://` reference.

### OPEC

Roadmap official-source baseline is retained for Monthly Oil Market Report / statistical publications. P10-A intentionally keeps transport in `METADATA_ONLY_REVALIDATION_REQUIRED`; no automated endpoint is selected or invented.

### IEA

Official Oil Market Report product:  
https://www.iea.org/data-and-statistics/data-product/oil-market-report-omr

Timely detailed OMR/MODS access is licensed. P10-A records `LICENSE_REVIEW_REQUIRED` and does not claim entitlement.

### World Gold Council

Official Goldhub data:  
https://www.gold.org/goldhub/data

WGC publishes demand/supply, reserves, ETF flows, trading-volume and other gold datasets. Some underlying benchmark/market data carry third-party rights, so automated production ingestion remains under licence review.

### LBMA

Official prices/data:  
https://www.lbma.org.uk/prices-and-data/lbma-precious-metal-prices

LBMA states that historical tabulated benchmark-price access requires the relevant IBA licence. Public clearing data is a separate source. P10-A therefore keeps historical benchmark transport behind licence review.

## Vintage compatibility

P10-A is compatible with the canonical P06-E Macro Vintage Model.

A later ingested observation must preserve, where available:

- official/provider release time;
- NEXUS QUANT observed-at time;
- source identity;
- source dataset/version evidence;
- raw payload lineage;
- revision identity.

If a source lacks native historical-vintage queries, NEXUS QUANT must not reconstruct historical knowledge from today's latest value. Instead, future live ingestion must persist each observed release/revision as it is received.

## Offline request specifications

P10-A allows deterministic **request specifications** for sources whose transport shape is sufficiently verified. These specs:

- do not execute a network request;
- allow only GET/POST;
- cannot escape the source's official host;
- require `secret://...` references for key-required sources;
- never resolve or serialize a raw secret;
- are marked `OFFLINE_REQUEST_SPEC_ONLY_NO_NETWORK`.

Licensed/revalidation-required sources cannot emit request specs.

## Explicit non-claims

P10-A does not certify:

- production credentials or subscriptions;
- availability/latency SLOs;
- first-release values or previous-at-time values;
- revision-history reconstruction;
- event calendar correctness;
- macro surprise;
- causal market impact;
- trade-success probability;
- BUY/SELL decisions;
- Risk approval;
- execution.

Those belong to later governed P10/P11/P12/P14+ workstreams.

## Safety

Production fundamental source: NOT_SELECTED  
Production network connection: DISABLED  
Credentials in repository: NONE  
Country assumption: NONE  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

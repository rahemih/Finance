# P01-D — Jurisdiction & Compliance Matrix

STATE = RESEARCH_BASELINE  
TASK = `FIN-P01-WD-001`  
PHASE = `P01 — Market / Provider / Compliance Research`  
LEGAL_ADVICE = `NO`  
OWNER_JURISDICTION = `UNSET_HUMAN_GATE`  
PRODUCTION_PROVIDER_SELECTION = `NOT_PERFORMED`  
LIVE_TRADING = `DISABLED`  
AUTO_TRADING = `DISABLED`

## 1. Objective

Define the compliance evidence that Finance / NEXUS QUANT must have before a market-data provider, broker, exchange or product can become production-eligible.

This document is a research baseline, not personalized legal advice.

It deliberately does **not** infer:
- residence;
- citizenship;
- tax residency;
- entity domicile;
- retail/professional/accredited status;
- broker/exchange eligibility

from ChatGPT metadata, network/location signals or prior conversations.

Those facts must be supplied explicitly by the Owner when a real account/provider decision reaches the Human Gate.

## 2. Current operating-model boundary

The baseline project is:
- private Owner/team use;
- research and own-account decision support;
- not public SaaS;
- not copy trading;
- not brokerage;
- not client asset custody;
- not an exchange or trading venue.

P01-D therefore does not conclude that the project itself requires a regulated-provider licence. That conclusion depends on the actual future activity, entity, clients and jurisdiction.

If the project later serves third parties, manages client funds, transmits client orders, offers advice/portfolio management as a business, operates a venue, or markets regulated services to others, the compliance analysis must be reopened before implementation.

## 3. Mandatory separations

The project must keep these concepts separate:

`MARKET_DATA_RIGHTS != TRADING_AUTHORIZATION`

`TECHNICAL_API_ACCESS != LEGAL_ELIGIBILITY`

`BROKER_ACCOUNT_APPROVAL != PRODUCT_ELIGIBILITY`

`PRODUCT_ELIGIBILITY != STRATEGY_APPROVAL`

`PUBLIC_ENDPOINT != REDISTRIBUTION_LICENSE`

`PAPER/DEMO_ACCESS != LIVE_TRADING_AUTHORIZATION`

A provider can be technically excellent and still be unusable because of jurisdiction, client class, licensing, contractual-use rights or product restrictions.

## 4. Owner / entity Human Gate

Before P01-G can make a production baseline decision for any broker/exchange/provider, the project must obtain explicit Owner facts for the relevant account/entity:

- country of residence;
- citizenship only where the provider/regime actually requires it;
- tax residency where onboarding/reporting requires it;
- individual vs legal-entity account;
- entity domicile if applicable;
- retail/professional/accredited/institutional status if applicable;
- intended products;
- intended venue/provider;
- whether the system is strictly self-trading or provides services to third parties.

No agent may guess these values.

## 5. Representative jurisdiction matrix

This is representative, not exhaustive. It gives the project a compliance framework for candidate-provider screening. The exact Owner/entity jurisdiction remains unset.

### 5.1 European Union / EEA

**Crypto**

Regulation (EU) 2023/1114 — MiCA — establishes a Union framework for crypto-asset service providers. It defines and regulates professional crypto-asset services such as trading-platform operation, exchange, custody, transfer, execution, order reception/transmission, advice and portfolio management.

Important project implication:
- a venue/provider serving EU clients must have the appropriate regulatory basis for the service/product;
- the project does not treat technical access to a crypto API as proof of EU service eligibility;
- private own-account trading by the Owner is not classified here as a CASP activity; that would require activity-specific legal analysis.

**Retail CFD / leveraged FX**

ESMA's product-intervention framework established retail CFD protections including:
- leverage limits;
- margin close-out;
- negative balance protection;
- inducement restrictions;
- standardized risk warnings.

Historical ESMA baseline:
- 30:1 major FX pairs;
- 20:1 non-major FX, gold, major indices;
- 10:1 other commodities/non-major indices;
- 5:1 individual equities/other reference values;
- 2:1 cryptocurrencies.

Because national competent authorities can implement/maintain product-intervention rules, the project must verify the applicable Member State/EEA regulator and current provider terms at account-opening time.

**Gate:** exact Member State/EEA state + client classification required.

Primary sources:
- EUR-Lex MiCA: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R1114
- ESMA CFD measures: https://www.esma.europa.eu/press-news/esma-news/esma-adopts-final-product-intervention-measures-cfds-and-binary-options

Legal Data Hunter also resolved MiCA directly from the official EUR-Lex corpus as `EU/EUR-Lex::32023R1114`.

### 5.2 United States

**Retail off-exchange Forex**

CFTC rules regulate off-exchange retail foreign-currency transactions. CFTC materials state that counterparties and intermediaries generally must fall within permitted/regulated categories, including RFED/FCM structures and other legally enumerated regulated financial entities.

17 CFR Part 5 is the current federal rule set for off-exchange foreign-currency transactions.

**Crypto / leveraged retail commodity transactions**

Current CFTC materials emphasize that certain leveraged, margined or financed retail commodity transactions may require execution on appropriately registered venues unless an exception/relief applies.

The project will not classify a specific crypto token/product under U.S. law in P01-D; product classification and venue eligibility are instrument-specific and can involve CFTC and/or SEC jurisdiction.

**Gate:** U.S.-person/resident/entity status and exact product/venue must be verified.

Primary sources:
- CFTC retail Forex final rule: https://www.cftc.gov/LawRegulation/FederalRegister/FinalRules/2010-21729.html
- eCFR 17 CFR Part 5: https://www.ecfr.gov/current/title-17/part-5
- CFTC/SEC crypto statement: https://www.cftc.gov/PressRoom/SpeechesTestimony/cftcsecjointcryptostatement090225

Legal Data Hunter independently found `US/eCFR::17_CFR_Part_5`.

### 5.3 United Kingdom

**Retail crypto derivatives**

FCA PS20/10 prohibits the marketing, distribution and sale in or from the UK to retail clients of derivatives and ETNs referencing certain unregulated transferable cryptoassets. The prohibition took effect on 6 January 2021.

This means a venue being technically accessible does not make retail crypto-perpetual/futures/CFD trading eligible for a UK retail client.

**Retail CFD / rolling spot Forex**

FCA PS19/18 and COBS 22.5 impose:
- leverage limits;
- 50% margin close-out;
- negative balance protection;
- inducement restrictions;
- standardized risk warnings.

COBS 22.5 sets:
- 3.33% minimum margin for major FX pairs, approximately 30:1;
- 5% for minor FX pairs and gold, approximately 20:1.

**Gate:** UK retail/professional classification + provider authorization required.

Primary sources:
- FCA PS20/10: https://www.fca.org.uk/publications/policy-statements/ps20-10-prohibiting-sale-retail-clients-investment-products-reference-cryptoassets
- FCA PS19/18: https://www.fca.org.uk/publications/policy-statements/ps19-18-restricting-contract-difference-products
- FCA COBS 22.5: https://handbook.fca.org.uk/handbook/COBS/22/5.html

### 5.4 Australia

ASIC's CFD product-intervention order applies retail protections including:
- leverage limits from 30:1 to 2:1;
- margin close-out;
- negative balance protection;
- restrictions on certain inducements.

ASIC extended the order through 23 May 2027 unless revoked or remade earlier. ASIC's 2026 review explicitly notes the upcoming 2027 expiry/review, so the rule must be revalidated before account activation.

The CFD framework can apply when the underlying is FX, indices, commodities or crypto-assets.

**Gate:** Australian retail/wholesale status and provider authorization required.

Primary sources:
- ASIC extension: https://www.asic.gov.au/about-asic/news-centre/find-a-media-release/2022-releases/22-082mr-asic-s-cfd-product-intervention-order-extended-for-five-years/
- ASIC 2026 review: https://download.asic.gov.au/media/tq0he35c/rep828-published-20-january-2026.pdf

### 5.5 Japan

Japan FSA materials describe:
- registration requirements for Crypto Asset Exchange Service Providers;
- regulation of crypto-asset derivatives under the Financial Instruments and Exchange Act;
- user-protection, custody, AML/CFT and solicitation requirements;
- a minimum 50% margin requirement for retail crypto-asset CFD transactions, corresponding to a 2:1 leverage ceiling.

FSA materials also indicate that leveraged FX/derivative intermediaries sit inside financial-instruments regulation and provider registration requirements.

**Gate:** Japanese residency/entity facts + FSA registration and product eligibility verification.

Primary sources:
- FSA crypto framework: https://www.fsa.go.jp/en/news/2022/20220914-2/02.pdf
- FSA crypto landscape/regulation: https://www.fsa.go.jp/en/news/2022/20221207/01.pdf

### 5.6 Singapore

**Digital Payment Token services**

MAS PS-G03 sets consumer-protection expectations for Digital Payment Token service providers, including:
- asset safeguarding;
- retail risk-awareness assessment;
- restrictions on incentives;
- restrictions on credit and leverage;
- restrictions involving leveraged DPT transactions and DPT derivative contracts for retail customers.

**Leveraged Forex / CFDs**

MAS states that companies conducting regulated activities under the Securities and Futures Act generally require a Capital Markets Services licence unless exempt.

Its regulated capital-markets product scope includes:
- OTC derivatives;
- exchange-traded derivatives;
- spot foreign exchange for leveraged foreign exchange trading.

**Gate:** retail/accredited/institutional status + provider licence/exemption required.

Primary sources:
- MAS PS-G03: https://www.mas.gov.sg/regulation/guidelines/ps-g03-guidelines-on-consumer-protection-measures-by-dpt-service-providers
- MAS CMS licence: https://www.mas.gov.sg/regulation/capital-markets/apply-for-licensing-or-registration-of-capital-market-entities/cms-licence

### 5.7 Dubai — VARA jurisdiction

VARA states that entities carrying out regulated VA Activities by way of business in Dubai must be authorized/licensed unless exempt.

The VARA framework covers Dubai mainland and free zones except DIFC.

A particularly relevant proprietary-trading fact:
- an entity actively investing its **own portfolio** in Virtual Assets at or above USD 250,000,000 equivalent during any rolling 30-day period must register with VARA;
- that proprietary-trader registration does **not** authorize VA service activities or allow trading assets belonging to others.

This is useful because NEXUS QUANT is currently an own-account/private system rather than a service to clients.

**Gate:** exact UAE location/regime must be identified first — Dubai/VARA, DIFC, ADGM or another UAE/federal regime cannot be treated as interchangeable.

Primary source:
- VARA licensing requirements: https://rulebooks.vara.ae/index.php/rulebook/licensing-requirements

### 5.8 Hong Kong

SFC identifies:
- Type 3 regulated activity = leveraged foreign exchange trading;
- Type 1 / Type 7 and AMLO licensing frameworks for certain centralized virtual-asset trading-platform activities.

SFC states that centralized virtual-asset trading platforms carrying on business in Hong Kong or actively marketing to Hong Kong investors are required to be licensed under the applicable regime.

**Gate:** client status, active-marketing rules and provider licence scope must be verified.

Primary sources:
- SFC licensing: https://www.sfc.hk/en/Regulatory-functions/Intermediaries/Licensing/Do-you-need-a-licence-or-registration
- SFC VATP: https://www.sfc.hk/en/Rules-and-standards/Virtual-assets/Virtual-asset-trading-platforms-operators

## 6. Market-data compliance

P01-B already established that technical API availability does not prove legal entitlement.

Every candidate data source must eventually have these fields resolved:

- internal display right;
- internal non-display right;
- automated analysis right;
- algorithmic-trading use right;
- historical storage right;
- raw-data retention right;
- derived-data creation right;
- model-training right;
- redistribution right;
- client-display right;
- audit-retention right;
- exchange/index entitlements;
- professional/non-professional classification;
- territorial restrictions;
- termination-time deletion/retention obligations.

### Important examples from P01-B

CME, ICE, Cboe, S&P DJI and Nasdaq index/exchange data use formal licensing/entitlement models. A free webpage, demo feed or technically accessible endpoint must never be treated as a production non-display/redistribution licence.

P01-E owns the commercial/licensing-cost review.

## 7. Broker / exchange eligibility checklist

Before any P01-G production decision:

1. Owner/entity jurisdiction supplied explicitly.
2. Client class supplied explicitly.
3. Provider/broker legal entity identified.
4. Official regulator and licence/registration verified.
5. Target product permitted for that client class.
6. Target leverage/margin permitted.
7. Spot vs perpetual/futures/CFD product classification verified.
8. API/automated trading allowed under provider terms.
9. Regional onboarding/KYC eligibility confirmed.
10. Account/entity type supports required API permissions.
11. Withdrawal authority can be disabled or isolated where possible.
12. Market-data rights cover internal/non-display/storage/derived use.
13. Tax/reporting obligations flagged for jurisdiction-specific professional review.
14. Sanctions/AML/provider-country restrictions checked.
15. Any knowledge/appropriateness tests or product warnings completed.
16. Evidence date and revalidation trigger stored.

## 8. Fail-closed rules

The compliance engine/governance must later enforce:

- Unknown jurisdiction or client class → `NOT_ELIGIBLE_FOR_PRODUCTION_SELECTION`.
- Conflicting provider terms vs regulatory rule → `BLOCKED_COMPLIANCE_REVIEW`.
- Product prohibited/restricted for retail → no offshore workaround, status misrepresentation or geofence/KYC bypass.
- KYC/AML/sanctions/provider-country controls must not be bypassed.
- No automation may change declared residency, client class or entity facts.
- Compliance uncertainty blocks Live eligibility.
- Offline research can continue with lawfully obtained/licensed data while execution remains blocked.

## 9. Handoff to later P01 workstreams

### P01-E — Cost / Licensing / Data Rights

Must resolve:
- subscription costs;
- exchange/index entitlements;
- professional/non-professional fees;
- non-display/algorithmic use;
- raw/historical storage;
- derived-data/model-training rights;
- redistribution/display;
- termination/retention clauses.

### P01-F — Primary / Backup Provider Strategy

Can only use candidates that have passed jurisdiction/product/client-class screening.

### P01-G — Provider Baseline Decision

Cannot make a production baseline decision until:
- Owner/entity jurisdiction is explicitly known;
- P01-D compliance facts are current;
- P01-E costs/rights are resolved;
- P01-F fallback/independence is defined.

### P03 / P24

P03 will implement identity/secrets/audit controls.  
P24 requires a fresh compliance/eligibility check before real-capital activation.

## 10. Result

Representative jurisdiction matrix = `CREATED`  
Owner jurisdiction = `UNSET_HUMAN_GATE`  
Personalized legal conclusion = `NONE`  
Production provider = `NOT_SELECTED`  
Broker/exchange = `NOT_SELECTED`  
Accounts/KYC/credentials = `NONE`  
Live Trading = `DISABLED`  
Auto Trading = `DISABLED`

Machine-readable evidence:
`docs/03-research/p01-d-jurisdiction-compliance.json`

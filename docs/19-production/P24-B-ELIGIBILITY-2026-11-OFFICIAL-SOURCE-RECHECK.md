# P24-B / Prerequisite #1 — official-source legal-entity and product screening refresh

**Date of review:** 2026-11-07. **Task:** `FIN-P24-WZ-001`. **Claim scope:** PUBLIC_PRIMARY_SOURCE_RESEARCH_ONLY. **Production verdict:** `OWNER_JURISDICTION_RESOLVED = UNSATISFIED` (external legal/entity/product acceptance not independently reviewed). **Owner input is complete**: actual legal residence, natural-person contracting class, and responsibility for future KYC with a provider were supplied in private conversation. No one should ask Owner to upload or undergo KYC for the assistant. Do not include private location, exact residential address, ID or account data in this public repository.

## Critical change since 2026-11-02 research: US OFAC listing

**Verified US primary issuer record:**
- 2026-06-02, OFAC [official Iran-related SDN action](https://ofac.treasury.gov/recent-actions/20260602) lists `NOBITEX` / `nobitex.ir`, `WALLEX` / `wallex.ir`, `BITPIN` / `bitpin.ir`, `RAMZINEX` / `ramzinex.com` as designated persons/entities. The SDN listing is not speculative.
- 2026-11-04, [official OFAC list-update notice](https://ofac.treasury.gov/recent-actions/20261104) still shows designated NOBITEX and BITPIN entries in the SDN amendments. This notice modifies secondary-sanctions descriptors; it does NOT document delisting.
- [OFAC FAQ 1257](https://ofac.treasury.gov/faqs/1257), updated 2026-08-07, explicitly warns that non-US persons and foreign financial institutions engaging with OFAC-designated Iranian exchanges may face secondary sanctions or correspondent-account restrictions. [FAQ 1250](https://ofac.treasury.gov/faqs/1250) describes blocking when property is within US jurisdiction or held by US persons.

**Interpretation:** US sanctions are a jurisdiction-specific legal/risk regime, NOT proof that a specific natural person within Iran is banned under Iranian law from all domestic spot activity. Conversely, local onboarding/KYC or API availability does NOT nullify OFAC exposure of US persons, foreign intermediaries, payment or cloud service vendors. **No designated exchange may be recommended/accepted for a cross-border or live NEXUS QUANT integration until independent sanctions/legal review explicitly permits the entire service/data/funding/counterparty topology.** No proxy/nominee/geolocation masking, sanction-evasion route or automated transfer is authorized or discussed as an implementation plan.

## First-party provider/entity evidence

| Research target | First-party source | What it actually establishes | Still missing; current verdict |
| --- | --- | --- | --- |
| FIBO Group Ltd (BVI) FX/CFD | [FIBO CAP PDF (10 pages)](https://www.fibogroup.com/u/document_file/2419/client_acceptance_policy.pdf), especially pages 1–2; [FIBO official legal docs](https://www.fibogroup.com/documents/); [FIBO public registration](https://www.fibogroup.com/products/clients/how-to-register/) | The CAP explicitly excludes Australia, Belgium, UK, North Korea, USA, and Russia* (Russian website condition); Iran is **not explicitly in that exclusion list**. It also reserves discretionary rejection and applies sanctions-list screening and due diligence. The **BVI FSC official regulator register** independently lists [FIBO Group Ltd as a currently regulated entity — Dealing as Agent](https://www.bvifsc.vg/regulated-entities/fibo-group-ltd), [Dealing as Principal](https://www.bvifsc.vg/regulated-entities/fibo-group-ltd-1) and [Arranging Deals in Investments](https://www.bvifsc.vg/regulated-entities/fibo-group-ltd-0) (issuer entries dated 2026-08-31, reviewed 2026-11-07). This verifies named regulated-entity/category presence, **not** the exact broker-claimed licence number `SIBA/L/13/1063`, which is not shown in these issuer records, nor a person/country/product-level customer acceptance. | Not a written guarantee of acceptance of an Iranian-resident natural person or of Forex/metal/energy CFD permissions, payment, data/MT5 rights. `CONDITIONAL_RESEARCH_CANDIDATE / NO_ACCOUNT_ACCEPTANCE`. |
| LiteFinance Global LLC (Saint Vincent and the Grenadines) FX/CFD | [exact entity comparison](https://www.litefinance.org/company/registered-offices/); [Swap-Free account countries](https://www.litefinance.org/trading/account-types/islamic-no-swap/); [legal documents](https://www.litefinance.org/company/documents/) | Global LLC itself officially states **Regulator: No** and **Complaints Authority: No**; other Mauritius or Cyprus LiteFinance entities hold different licences, not transferable to this LLC. Iran appears on a feature-level Swap-Free availability page. | No entity-specific written Iranian-resident individual LIVE FX/metal/energy CFD acceptance, source rights, compensation, margin and funding/withdrawal agreement; no regulatory supervision proven for Global LLC. `HIGH_COUNTERPARTY_RISK / UNSELECTED`. |
| Nobitex/Bitpin/Wallex/Ramzinex domestic crypto | Primary first-party product/registration and API documentation plus **OFAC sources above** | Iranian local spot/credit APIs may be offered subject to the provider's own terms. Credit/`تعهدی` is **not evidence** of conventional perpetual or dated futures, USDT/coin-margined settlement, nor permission to automatically execute trades across international infrastructure. Official US sanctions listing is an externally verified cross-border counterparty concern. | Independent Iranian regulator-issued licence/acceptance, product-specific contract, data/API licence, assets/symbol coverage, funds and safe cross-border service topology all unverified; `SANCTIONS_RISK_REVIEW_REQUIRED / NO_NEXUS_LIVE_INTEGRATION`. |
| Kraken and other excluding venues | [Kraken official location restrictions](https://support.kraken.com/articles/where-is-kraken-licensed-or-regulated) | Iran on official prohibited-client list. | `EXCLUDED_FOR_OWNER_RESIDENCE_SCENARIO`; do not apply or seek geographic bypass. |

## Independent prerequisites and decision

Only **substeps** for owner's country, personal account class, and self-managed future provider KYC are complete. The canonical policy `OWNER_JURISDICTION_RESOLVED` includes **legal eligibility of the exact provider contracting entity + customer class + each instrument/product**, and requires an independent compliance decision backed by actual current authoritative sources. Therefore **the canonical control remains unsatisfied (FALSE)**.

**Acceptance matrix for each future venue:** name of exact legal entity; jurisdiction and issuer/regulator verifiable official record (BVI FSC named FIBO entity/category now VERIFIED, exact self-claimed licence number and Iranian customer product eligibility remain UNVERIFIED); allowed Iranian resident natural-person onboarding; separate FX/commodity CFDs, crypto spot, perpetual and dated futures permissions; permitted API/non-display data/risk system usage; custody, payments and withdrawals; sanctions/international infrastructure exposure; terms effective date; independent reviewer identity recorded privately; evidence digest, expiration and triggers for invalidation.

**Do not conflate** broker-branded CFD crypto feeds with actual crypto spot ownership or exchange futures. FIBO country-list omission is only absence of explicit exclusion, NOT positive legal permission. LiteFinance Swap-Free availability is a feature, NOT guaranteed eligible onboarding. Consumer product pages or third-party promotion cannot substitute legal terms and regulatory issuer verification.

### Provider-side confirmation matrix (prepared, not sent)

The following generic questions should be answered **in writing by an official compliance/licensing contact at each exact prospective contracting entity**, without the Owner sending identity documents or account credentials here. No message has been sent by this research task.

1. Do you accept a legally resident Iranian **natural person**, acting on their own account, for a live account under the precise legal entity in the proposed agreement? Identify any restrictions, identity/KYC done **directly by your provider**, and the currently effective legal/contractual basis.
2. Are FX currency-pair CFDs, gold/silver CFDs and energy/oil/natural-gas CFDs permitted for this client type? Separately list crypto spot ownership versus CFD crypto exposure, and whether perpetual or expiry-dated futures and stablecoin/coin margin are actually offered and eligible.
3. Are MT5 and/or official API **read-only market data**, non-display algorithmic analysis, automated risk-veto and broker-sanctioned order sandbox licensed for this jurisdiction/client/product? What written rights and limits apply to 10 internal users and the data provider?
4. What entity-specific regulator/registration number and official issuer record support this service? Which sanctions/export rules, banking intermediaries, settlement currencies, deposits, withdrawals, custody rules, and outages apply? Are contractual funds and withdrawals serviceable without evading restrictions?
5. Can you supply a dated signed/official written confirmation and exact linked current terms for independent assessment? **A marketing page, a country-list omission and a Demo account are not affirmative client-specific eligibility approval.**

Answers must be independently reviewed by qualified compliance authority and signed off in the governed evidence register. Do not send account numbers, KYC documents, identity photos, residential addresses or credentials into public repositories or this questionnaire.

### Correct next action (without new owner identity questions)

Conduct official regulator and entity-specific source verification and draft a neutral **non-sensitive provider eligibility confirmation request**. Only a provider's affirmative written answer plus independent validation can change its candidate verdict. The Owner will personally manage future KYC if a valid provider is selected. No contact message is sent and no account, key, or money is handled by this task.

**Production invariant:** PRE_FIRST_LIVE 0/9 satisfied; P24-B BLOCKED; FIRST_LIVE_OWNER_GATE NOT_GRANTED; P24-C..I NOT_STARTED; G13 NOT_STARTED; LIVE/AUTO DISABLED. A5 independent veto, A8 security, A10 reproducible evidence, mandatory Owner PR gate remain nonwaivable. S0 and read-only Demo observations do not establish legal onboarding or real broker certification.

### Reference pointers
- [Live evidence tracker #491](https://github.com/rahemih/Finance/issues/491)
- [Prior 2026-11-02 research](P24-B-PROVIDER-ELIGIBILITY-AND-DATA-RIGHTS-RESEARCH.md)
- [PRE_FIRST_LIVE nine-control register](P24-B-PRE-FIRST-LIVE-UNBLOCK-REGISTER.md)
- [Production readiness config](../../config/production/production-readiness-dossier.json)

**Rollback:** Only this correction and index/contract; never modify runtime permissions, P24-B status, sanctions rules, config or broker connections.

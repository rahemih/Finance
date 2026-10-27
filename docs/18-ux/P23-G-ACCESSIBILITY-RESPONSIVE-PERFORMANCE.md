# P23-G — Accessibility / Responsive / Performance

Task: `FIN-P23-WG-001`  
Status: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P23-WG-001-01` / RELEASED  
Claim scope: `REFERENCE_FRONTEND_VALIDATION`

## Accessibility

Reference target:
- WCAG 2.2 AA;
- normal text contrast >= 4.5:1;
- large text contrast >= 3:1;
- minimum touch target 44 px;
- visible focus required;
- keyboard operability required;
- reduced motion required;
- color-only semantics forbidden;
- semantic labels required;
- critical table/chart alternatives required.

## Responsive coverage

Canonical reference viewports:
- mobile: 360 px;
- tablet: 768 px;
- desktop: 1024 px;
- wide: 1440 px.

All eleven P23-C operational screens must remain covered. Critical content clipping is forbidden. Dense financial tables may use explicit horizontal scrolling. RTL shell and isolated LTR financial islands must remain intact.

## Performance budgets

Reference Core Web Vitals budgets:
- LCP <= 2500 ms;
- INP <= 200 ms;
- CLS <= 0.1.

These are deterministic reference budgets for implementation/regression validation. P23-G does not certify real-user or production performance.

## Safety

No credentials, external-order authority, runtime mutation/remediation, production/P24 activation or Live/Auto trading authority.


## Canonical closure evidence

- implementation PR #483 = MERGED;
- final implementation head = `90302a63eb764c6f5c9d18cdf262c91b2819b621`;
- implementation Governance = `40498290125` / SUCCESS;
- implementation artifact = `12731272914` / `sha256:8dd746b0a3d8a7e3d7b88dabd29006b2f1e629dc7467d19e778ed85e53f243fb`;
- policy ID = `2ccbf18e8791223f8cc18788b1495b32ab9dbc849cc77f0b08ee36a004bf480c`;
- evidence ID = `a062683ac936d95be61fd024f8a3add43f7b0920e2872401f327e3f555683324`;
- deterministic evidence SHA256 = `16a8066a19668549b2cd6ff9dd60d6a663d97bb273e63ef136f7fcef85e47b4e`;
- implementation merge = `44e81c48e68e02f53944e74eb3dd431749e66664`;
- post-merge Governance = `40498631397` / SUCCESS;
- post-merge artifact = `12731752456` / `sha256:ca952f7d39e8fd4b6d27530e955c4a9d4bad64e8d445f02efbdef8409415b57e`;
- post-merge Branch Hygiene = `40498630956` / SUCCESS.

P23-H = READY_NOT_STARTED.  
P23-I = NOT_STARTED.  
P24 = NOT_STARTED.  
LIVE_TRADING / AUTO_TRADING = DISABLED.

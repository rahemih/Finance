# P23-G — Accessibility / Responsive / Performance

Task: `FIN-P23-WG-001`  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WG-001-01` / ACQUIRED  
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

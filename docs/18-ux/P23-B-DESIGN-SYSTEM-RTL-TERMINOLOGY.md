# P23-B — Design System / RTL / Terminology

Task: `FIN-P23-WB-001`  
Status: IN_PROGRESS  
Lock: `LOCK-FIN-P23-WB-001-01` / ACQUIRED

## Objective

Create the product-owned visual and language contract that all P23 operational screens must consume.

## Directionality

- application shell and Persian narrative: RTL;
- canonical financial identifiers: LTR islands with bidi isolation;
- tickers, OHLC, prices, quantities, percentages, order/trade IDs, hashes, ISO timestamps, versions and IP addresses remain LTR;
- financial values and identifiers use Latin digits; localized narrative counters/calendar labels may use Persian digits.

## Typography

Canonical Figma intent:
- Persian UI: Noto Sans Arabic;
- Latin financial content: Noto Sans.

Production font packaging remains governed by licensing/build policy; P23-B defines the product intent and fallback boundary, not CDN/runtime delivery.

## Themes

Dark mode is first-class. Both light and dark themes define background, surface, body/muted text, border and focus tokens. Body/muted text contrast is validated against WCAG 2.2 AA minimum 4.5:1.

## Semantic states

Product-owned state semantics:
- success;
- warning;
- critical;
- stale;
- degraded;
- no-trade;
- disconnected;
- pending.

Every state requires both a text label and icon cue. Color-only meaning is forbidden.

## Density

- monitoring density: compact table rows/cards for watch surfaces;
- analysis density: roomier rows/cards for deep inspection.

## Terminology

Persian-first labels are paired with canonical identifiers. Trading direction and decision identifiers remain visible:
- خرید (LONG)
- فروش (SHORT)
- انتظار (WAIT)
- عدم معامله (NO_TRADE)

## Product-owned component families

P23-B governs variants for:
- NexusAppShell;
- MetricCard;
- RiskBadge;
- MarketStatusBadge;
- EmptyState;
- DegradedState;
- StaleDataBanner.

P23-C may implement these above third-party primitives but may not change their semantic contract silently.

## Safety

No external orders, runtime mutation/remediation, credentials, production/P24 activation or Live/Auto trading authority are created by this workstream.

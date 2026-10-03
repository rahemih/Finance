# NEXUS QUANT — Frontend Excellence Baseline

STATE = GOVERNED_RESEARCH_BASELINE  
TASK = `FIN-P01-WUI-001`  
LINEAR = `HOS-112`  
EFFECTIVE_DATE = 2026-10-03  
RUNTIME_IMPLEMENTATION = NOT_STARTED  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED

## 1. Purpose

This document defines the non-library capabilities required to make NEXUS QUANT fast, accessible, reliable, visually coherent, measurable, and maintainable. It complements the repository registry and is intentionally implementation-neutral.

## 2. Design system

Required:
- canonical Figma source for UX intent before P23 implementation;
- design tokens for color, spacing, typography, radii, elevation, breakpoints and semantic states;
- semantic state tokens for success, warning, critical, stale, degraded, no-trade, disconnected and pending;
- component variants documented before page duplication occurs;
- dark mode as first-class;
- RTL Persian application shell with explicit LTR numeric/financial islands;
- density modes for monitoring vs deep analysis;
- reusable layout primitives for dashboard, split-pane analysis and report pages.

Design-system artifacts must remain product-owned even when third-party primitives are used.

## 3. UX and information architecture

Required:
- task-oriented navigation;
- command palette / keyboard navigation for power users;
- progressive disclosure for dense financial information;
- saved views and filters;
- responsive behavior defined per page family, not generic shrink-to-mobile;
- mobile monitoring priorities: watchlist, alerts, positions, risk, system health;
- empty/loading/error/offline/stale/degraded states for every critical surface;
- state changes must not rely on color alone;
- clear source/timestamp provenance near sensitive analytics.

## 4. Performance baseline

Before P23 implementation, define measurable budgets for:
- initial JS bundle;
- route-level code size;
- LCP/INP/CLS;
- API latency classes;
- chart render latency;
- table virtualization thresholds;
- memory growth under realtime updates;
- reconnect/recovery time;
- maximum background polling rate.

Architecture rules:
- route-level code splitting;
- lazy load heavy chart/research modules;
- virtualize large tables/logs;
- cache immutable/static assets;
- preload only critical fonts/assets;
- avoid client rendering for content that can be safely server rendered;
- no global polling loop when event streaming is available.

## 5. Rendering/data-delivery strategy

Each page must explicitly classify data as:
- static/reference;
- request/response;
- cached server state;
- realtime stream;
- user-local ephemeral state.

Prefer:
- SSR/streaming for shell/reference content where useful;
- query caching for request/response server state;
- WebSocket/SSE for realtime market/system updates where justified;
- optimistic updates only for reversible user actions;
- stale-while-revalidate patterns for non-critical analytics;
- hard freshness indicators for trading-relevant data.

## 6. Realtime UX

Required:
- connection status;
- source/provider indicator;
- last update timestamp;
- stale threshold;
- reconnecting/degraded state;
- backpressure/aggregation strategy for high-frequency updates;
- frame-rate protection so charts do not render every raw tick;
- bounded in-memory history;
- graceful provider failover visualization;
- no silent fallback from realtime to stale data.

## 7. Accessibility

Target:
- WCAG 2.2 AA baseline.

Required:
- keyboard-only navigation;
- visible focus states;
- semantic landmarks/headings;
- accessible form labels/errors;
- contrast verification;
- reduced-motion support;
- screen-reader announcements for critical asynchronous state changes;
- touch targets suitable for mobile;
- table/chart alternatives where critical meaning would otherwise be inaccessible.

## 8. Data visualization standard

A dedicated visualization specification must define:
- bullish/bearish/neutral semantics;
- uncertainty/confidence display;
- stale/missing data representation;
- timestamp/timezone conventions;
- logarithmic vs linear scale rules;
- volume and proxy-volume labeling;
- signal/entry/stop/target marker conventions;
- indicator legends;
- comparison normalization;
- color-blind-safe state distinctions.

Charts are explanatory surfaces, never the source of trading truth.

## 9. Forms and safety UX

Required:
- schema-driven validation;
- inline validation without destructive surprises;
- explicit confirmation for sensitive actions;
- disabled/permission-aware states;
- session expiry handling;
- recovery flow for 2FA/passkey;
- device/session management;
- audit-friendly confirmation text for consequential settings.

## 10. Testing strategy

Minimum frontend test pyramid:
- unit tests for pure view logic/formatters;
- component tests for reusable financial components;
- contract tests against API schemas;
- visual regression tests for critical pages/components;
- accessibility checks;
- E2E tests for login -> dashboard -> asset -> signal -> report;
- responsive viewport coverage;
- realtime disconnect/reconnect tests;
- performance regression tests;
- reduced-motion/dark-mode/RTL checks.

Critical flows may not rely only on snapshot tests.

## 11. Visual regression

Required for:
- auth;
- dashboard;
- market/asset detail;
- trading/risk tables;
- reports;
- system health;
- settings/security.

Golden snapshots must be reviewed through governed changes rather than silently updated.

## 12. Observability and product telemetry

Frontend must expose:
- JavaScript/runtime errors;
- API error rate;
- route load time;
- Core Web Vitals;
- slow component/chart rendering;
- websocket reconnect counts;
- stale-data duration;
- failed user actions;
- feature-level usage only where privacy/governance permits.

Trading/audit truth must not live only in product analytics.

## 13. Feature flags

Use feature flags for:
- incomplete pages;
- experimental analytics;
- new chart overlays;
- beta agent surfaces;
- risky settings;
- staged rollout.

Flags must have owner, expiry/review trigger and safe default.

## 14. Mocking and contract-first development

Frontend implementation should not wait on backend completion.

Required:
- OpenAPI/JSON Schema/typed contract source of truth;
- generated or contract-checked types;
- deterministic mock fixtures;
- loading/error/empty/stale fixture states;
- representative large datasets for table/chart performance testing.

## 15. Internationalization and locale

Even with Persian-first UX:
- no hard-coded user-facing strings in reusable components;
- timezone handling explicit;
- locale-aware number/currency formatting;
- Persian/Latin digit policy documented by context;
- financial identifiers stay canonical;
- dates use clear timezone/source semantics.

## 16. PWA/offline capability

Candidate scope:
- installable shell;
- offline access to non-sensitive static/help content;
- last-known watchlist/dashboard snapshot where safe;
- push notification capability if later approved;
- clear offline/stale banner;
- no order/trading action presented as successful while offline.

PWA adoption is conditional on security/privacy review.

## 17. Personalization

Candidate capabilities:
- saved filters;
- saved table columns;
- pinned assets;
- configurable dashboard widgets;
- density preference;
- theme preference;
- alert preferences.

Personalization must never hide mandatory risk/compliance notices.

## 18. Security UX

Required:
- session/device visibility;
- suspicious-login/new-device notification pattern;
- permission-aware UI;
- explicit handling of revoked/expired sessions;
- CSRF/XSS-safe rendering conventions;
- no secrets in browser storage;
- no security-sensitive state inferred only from client-side checks.

## 19. Font and asset strategy

Required:
- limited production font families;
- subset Persian fonts where licensing permits;
- preload only above-the-fold critical weights;
- SVG/icons preferred over raster for UI;
- responsive images;
- CDN/cache headers;
- no oversized decorative media on analytical routes.

## 20. Engineering productivity

Recommended:
- isolated component preview environment (Storybook-class or framework-native equivalent);
- reusable fixtures;
- lint/typecheck/formatted commits;
- route/page ownership map;
- component documentation;
- ADRs for major frontend decisions;
- CI performance/accessibility/visual checks;
- preview deployment for PR review.

Exact tooling is selected later by benchmark and license/security review.

## 21. Phase ownership

- P02: frontend boundaries, rendering/data/realtime architecture.
- P03: auth/security UX, browser threat model, session policy.
- P04: package/tool selection, CI quality gates, build/bundle policy.
- P05/P06: streaming/data freshness contracts.
- P17/P18: model/experiment presentation and evidence UX.
- P22: observability, incident/degraded-mode UX.
- P23: design system, pages, responsive UI, PWA candidate, accessibility and final implementation.
- P24: final validation/hardening.

## 22. Definition of excellence

A frontend is not considered production-ready unless it is:
- usable;
- measurable;
- accessible;
- resilient to data/provider failures;
- responsive;
- fast under realistic data volume;
- secure by architecture;
- visually coherent;
- testable;
- traceable to source data and system state.

# NEXUS QUANT — WEB-P0 Visual Fidelity, Architecture & QA Acceptance Contract

- **Contract:** VF-2026-10-31-v1.0 / ARCH-2026-10-31-v1.0 / QA-2026-10-31-v1.0
- **Source document:** [NEXUS QUANT — Web Runtime MASTER WORKING DRAFT v0.8](https://docs.google.com/document/d/19trhKWaIB9YUqc3h7sgrovKwRiJKFUM_RSjmj6NDPQ0/edit) — native paragraphs 20.2–20.4
- **Scope:** 34 WEB-P0 pages, 212 design screenshots; **owner-directed mandatory implementation requirements**
- **Source-of-truth precedence:** GitHub main/FROZEN_G2/P03/P23 authoritative for deployed or merged code; conflicts must be resolved through governance before implementation
- **State:** `DOCUMENTATION_ONLY / CONTRACT_PROPOSED_FOR_REVIEW`; screenshots `REVIEW_REQUIRED`; owner-approved visual baseline, app implementation and runtime tests `NOT_VERIFIED`
- **Non-authority:** does not authorize source implementation, deployment, execution, broker connection, Live/Auto, P24, owner gate bypass or relaxation of Risk/Firewall controls
- **Design asset policy:** references to screenshots live in the Google Doc, not copied as large binaries to this PR; future versioned asset manifest + checksums and owner approval required before screenshot acceptance
- **P23 alignment:** [information architecture](../../config/ux/information-architecture.json), [design system](../../config/ux/design-system.json), [accessibility requirements](../../config/ux/accessibility-responsive-performance.json), [P23 reference E2E](P23-I-E2E-VALIDATION.md)

> This document transcribes the binding owner-requested contract from the Google Doc without claiming implementation. No active CI, E2E, screenshot comparison, native Google Docs alt-text completion, or Live approval is implied.

۲۰.۲ Visual Fidelity — Mandatory Acceptance Contract (VF-2026-10-31-v1.0)

وضعیت: MANDATORY_OWNER_DIRECTIVE برای توسعه WEB-P0؛ این قرارداد شرط رسمی اجرای آینده است، نه ادعای Approved Baseline، تست واقعی، Merge یا تأیید معاملات. در تعارض با GitHub main/P23/FROZEN_G2، تصمیم امن FAIL-CLOSED و اصلاح با ADR/PR و تأیید Owner لازم است.

VF-001 — الزام تطابق کامل: تمام ۳۴ صفحه و ۲۱۲ سناریو/تصویر WEB-P0 باید از نظر چیدمان، رنگ، فونت، اندازه، فاصله، آیکون، متن، تعامل و نمایش حالت‌ها، RTL/LTR، سلسله‌مراتب، جدول/نمودار، نشانگر امنیت/ریسک و واکنش‌گرایی با تصاویر مرجع متناظر انطباق داشته باشند. تصاویر مرجع قراردادند، نه الهام؛ هر تفاوت بصری یا معنایی تأییدنشده نقص است. تطابق ۱۰۰٪ یعنی صفر اختلاف تأییدنشده، نه یکسان بودن بیتی پیکسل‌ها در سیستم‌عامل‌های مختلف.

VF-002 — Baseline و وضعیت مالک: تصاویر موجود ۲۱۲/۲۱۲ و دارای شناسه‌های XXX-YY هستند، ولی بخش‌های REVIEW_REQUIRED بدون تأیید صریح Owner به APPROVED_BASELINE تبدیل نمی‌شوند. هر تصویر قبل از Frozen Baseline به pageId، route، screenshotId، state، viewport، theme، fixtureId، browser/DPR، SHA-256 و ownerReviewStatus متصل شود. تأیید الزام Visual Fidelity به‌معنای تأیید تک‌تک تصاویر نیست.

VF-003 — منبع طراحی: Design Tokens واقعی GitHub در config/ux/design-system.json و P23-B مرجع رنگ/فونت/Spacing/Radii/Focus/Semantic States است؛ فونت فارسی Noto Sans Arabic و مالی لاتین Noto Sans، نسخه‌ها و مجوزشان در PR ثابت شوند. تفاوت تصاویر با توکن‌ها «Design Conflict» بوده و فقط با Change Request و Owner Approval حل می‌شود. Dark در تصاویر مرجع الزام‌آور؛ Light نیز بر اساس توکن‌های Canonical جدا تست شود. Figma جدید موردنیاز نیست؛ سابقه تاریخی P23 حفظ شود.

VF-004 — نماهای پاسخ‌گو: در هر تصویر، ابعاد دقیق همان مرجع ثبت و مقایسه شود؛ ۳۶۰px، ۷۶۸px، ۱۴۴۰px پروفایل پایه و ۱۰۲۴px پروفایل اضافی، همراه آزمون reflow در ۳۲۰px و Zoom=200٪. اسکرول افقی فقط در جدول‌های عریض با کنترل آشکار مجاز است؛ هیچ محتوای حساس، Risk Warning یا Action مهم نباید بریده/پنهان شود. مبنای تصاویر 028-03 و 029-03 نسخه‌های اصلاح‌شده ۳۶۰×۶۴۰ است.

VF-005 — مقایسه قابل‌بازتولید: Playwright با browser/version/OS/container، deviceScaleFactor، locale=fa-IR، timezone، fonts-loaded و motion-disabled ثابت؛ Fixtures نسخه‌دار و deterministic برای قیمت، ساعت، شناسه، وضعیت و خطا. تغییر مقادیر واقعی مجاز است، اما قالب، برچسب، محل، واحد، کیفیت و معنای نمایش باید برابر باشد. Mask پویا فقط با ثبت ناحیه/دلیل/expiry/تأیید Owner؛ Mask متن، کنترل، Badge، Risk، Error یا Security ممنوع.

VF-006 — معیار عددی Visual Regression: در محیط مرجع پین‌شده، نسبت پیکسل‌های متفاوت پس از RGB channel threshold=۱۲/۲۵۵ حداکثر ۰٫۵٪ و SSIM حداقل ۰٫۹۹۵ باشد؛ هر دو شرط باید هم‌زمان PASS باشند. این تلورانس فقط نویز رندر/anti-aliasing را پوشش می‌دهد و به هیچ تفاوت قابل‌تشخیص یا معنایی اجازه نمی‌دهد. اختلاف ساختاری، تایپوگرافی معنی‌دار، رنگ معنایی، متن، هشدار، نقش، CTA و اولویت محتوا حتی زیر عدد آستانه FAIL است. Threshold فقط با ADR و مالک قابل تغییر است.

VF-007 — مناطق بحرانی: پیام‌های NO_TRADE/WAIT، UNKNOWN/STAlE/DEGRADED، لغو/ارسال سفارش، Risk Veto، وضعیت Session، خطای Auth، کیفیت داده و Kill Switch باید از نظر محتوا و ترتیب بدون هیچ اختلاف معنایی نمایش داده شوند؛ رنگ به‌تنهایی حامل معنا نباشد. Scanner فرصت مجوز ورود نیست، ORDINAL ranking احتمال P14 نیست و هیچ UI، Risk P15/Firewall P16/OMS P20 را دور نمی‌زند.

VF-008 — خروجی الزامی هر Screenshot: Artifact شامل baselineSHA256، testedCommitSHA، Playwright runId، fixtureId، environment، viewport/DPR/browser، screenshotActual، diffImage/overlay، pixelDiffRatio، SSIM، بررسی Critical Regions، Reviewer/Owner و نتیجه PASS/FAIL/NOT_RUN ذخیره شود. هر اختلاف نیازمند Issue/Decision-ID و Owner Approval است. بدون Baseline تأییدشده، نتیجه نهایی Visual ACCEPTANCE قابل ادعا نیست.

VF-009 — شرط پذیرش جامع: هر ۲۱۲ مورد باید Baseline تأییدشده، Visual Diff و Semantic/A11y Test مستند و PASS داشته باشند؛ تعداد اختلاف تأییدنشده = صفر، تست اجرا‌نشده = صفر و مورد Critical/High باز = صفر. صرف تعداد ۲۱۲ تصویر یا درصد شباهت بالا کافی نیست. تغییر بدون اجازه مالک، تغییر قالب/وضعیت/Route یا حذف تصویر مرجع ممنوع است.

VF-010 — Registry نسخه‌دار در Git: Screenshot Manifest شامل ID، صفحه، Route، State، تصویر مرجع، SHA، داده Fixture، DesignTokenVersion، Source/PR/CI، تأیید مالک و آخرین نتیجه Regression؛ فایل‌های بزرگ بی‌رویه وارد main عمومی نشوند و Assetهای ثابت و بهینه با checksum مدیریت شوند.

۲۰.۳ قرارداد معماری اجرایی Frontend/Backend (ARCH-2026-10-31-v1.0)

ARCH-001 — Stack: Code-First، React/Next.js/TypeScript در apps/web از همان Polyglot Monorepo رسمی. نسخه Node و pnpm مطابق package.json ریشه؛ نسخه نهایی Next/React، Auth/Chart/Table و Lockfile با Compatibility، License، SBOM، CVE و ADR پیش از Freeze ثبت شود. UI Components/Styles مشترک از config/ux/design-system.json و بسته P23-B ساخته شوند، نه از ظاهر حدسی هر صفحه.

ARCH-002 — مرز امنیت: Browser ⇄ HTTPS Same-Origin BFF/Auth Gateway ⇄ سرویس‌های Backend/Domain Adapters. هیچ ارتباط مستقیمی از Browser با Broker/Exchange، DB، Risk Policy، OMS، Vault، Audit DB یا Provider Key مجاز نیست. SSR Shell بدون افشای اطلاعات Session و Server-Side Identity/RBAC/Step-Up و Audit طبق P03/P23-H باشد.

ARCH-003 — API پیشنهادی: namespace /api/v1/... فعلاً PROPOSED است. برای هر API قبل از اتصال واقعی: Domain Owner، نسخه OpenAPI/JSON Schema، generated TypeScript types، Request/Error Envelope، Authentication، Environment/Role/Resource scope، HTTP status، pagination و Contract Test لازم است. مرورگر هیچ تصمیم Risk/Order را محاسبه یا تأیید نمی‌کند.

ARCH-004 — Realtime: فقط در صفحه‌های دارای Backend واقعی، SSE/WebSocket با resume/sequence، gap-detection، backoff و freshness/quality؛ روش نهایی transport per-domain با ADR و سنجش Runtime انتخاب می‌شود. Unknown/Stale/Offline به صفر یا OK تبدیل نشده و کنترل خطرناک Fail-Closed خواهد بود.

ARCH-005 — Auth و Privacy: Secure/HttpOnly/SameSite Cookie، CSRF/Origin برای Mutation، Backend RBAC/IDOR/Step-Up، CSP/XSS-safe for News/AI، Secret/Token هرگز در localStorage، URL یا Console. Visibility در UI برابر Permission نیست؛ تایید عملیات فقط در Domain Server مجاز است.

ARCH-006 — مالکیت اجزا: apps/web فقط UI/Presentation/Composition/BFF؛ Domain contracts در packages/contracts و منطق سرویس در مالک Domain، Provider SDK در adapters/؛ هیچ dependency تولیدی به research/ نباشد. مرزهای P05/P07/P13/P14/P15/P16/P18/P20/P21/P22/P23 و Independent A5 veto باید حفظ شوند.

ARCH-007 — Route و State: ۳۴ WEB-P0 زیرمجموعه ۱۱ Surface canonical P23 هستند؛ برای /research، /reports، /glossary و مسیرهای P1/P2 که هنوز پیاده نشده‌اند Disabled/Placeholder/404/403 امن و آشکار لازم است، نه صفحه جعلی. هر صفحه Loading/Empty/Error/Offline/Stale/Degraded و State تخصصی با Story/Fixture/Test-ID مستقل داشته باشد.

ARCH-008 — انتخاب‌های باز: Host، سرویس Identity/Passkey، نوع BFF/Route Handler، Transport، OpenAPI نهایی و Libraryها تا ADR و Review مصوب «قطعی» محسوب نمی‌شوند. محیط‌های DEV/TEST/RESEARCH/DEMO/SHADOW از CANARY/LIVE جدا؛ LIVE_TRADING/AUTO_TRADING = DISABLED و P24-G13 مستقل باقی می‌مانند.

۲۰.۴ قرارداد آزمون و پذیرش پیاده‌سازی (QA-2026-10-31-v1.0)

QA-001 — DoR هر صفحه: Page ID/Route و User Flow، screenshotIds و Owner Baseline Review، Field/API/Source Schema، permission matrix، Error/State matrix، Token Map، Fixture، Test IDs، dependencies و rollback plan. اگر بخش لازم مشخص نباشد status = BLOCKED_REVIEW.

QA-002 — CI لازم: lint/typecheck/unit/component، OpenAPI/Contract tests، integration، Visual Regression تمام سناریوهای مرتبط با مرورگر ثابت، keyboard و Screen Reader واقعی، axe+WCAG 2.2 AA، Security (RBAC/IDOR/CSRF/XSS)، error/retry/reconciliation و browser E2E. Playwright در ۳۶۰/۷۶۸/۱۰۲۴/۱۴۴۰ همراه reflow ۳۲۰ و Zoom=200٪ اجرا شود.

QA-003 — اهداف کمی موجود P23-G: contrast متن عادی ≥۴٫۵:۱، متن درشت ≥۳:۱، touch target ≥۴۴px، LCP ≤۲۵۰۰ms، INP ≤۲۰۰ms، CLS ≤۰٫۱؛ حداکثر صفر clipping بحرانی، صفر رنگ بدون معنای متنی، صفر نقص Safety و صفر تفاوت بصری تأییدنشده. Test Automation بدون آزمون دستی Screen Reader کافی نیست.

QA-004 — حالت‌های الزامی امنیت/معاملات: P13 expiry/no-chase، P14 probability evidence، A5 independent risk veto، P16 firewall، P20 unknown ACK و idempotency/reconciliation، invalid source/hash/freshness/FX/NAV، Demo checkpoint، Kill Switch؛ در نبود یقین، عمل حساس disabled و وضعیت قابل رؤیت باشد.

QA-005 — Evidence و پذیرش: Build URL، branch و exact SHA، baseline IDs و fixture IDs، CI run logs، diff images، matrix ۲۱۲ سناریو، Security/Accessibility/Contract results، Owner review و postmerge verification در GitHub/Linear پیوند بخورند؛ هیچ UI یا PDF/DOCX تصویر جایگزین تست کد نیست.

QA-006 — مراحل وضعیت: IMAGE_INVENTORY_COMPLETE (فعلاً برقرار) ≠ OWNER_BASELINE_APPROVED (باز) ≠ WEB_IMPLEMENTED (باز) ≠ E2E/CONTRACT/ACCESSIBILITY_PASSED (باز) ≠ OWNER_UI_ACCEPTED (باز) ≠ LIVE_APPROVED (مستقل و مسدود). انتشار UI فقط با ۳۴/۳۴ صفحه، ۲۱۲/۲۱۲ مقایسه تصویری PASS، صفر نقص بحرانی/High و تأیید Owner. P24/Broker/Live authorization هرگز از این پذیرش حاصل نمی‌شود.

QA-007 — وضعیت لحظه ثبت: اسکرین‌شات‌ها ۲۱۲/۲۱۲ در سند هستند؛ Native Alt Text همه تصاویر در Google Docs هنوز تأیید نشده، آزمون واقعی Backend/Browser و تأیید فردی Baseline باز است. این الحاقیه برای ثبت در Git و اجرای CI در PR بعدی آماده می‌شود؛ ادعای انجام PR یا تست در همین مرحله ممنوع است.


---

## Registration / Human Gate

- Scope is **docs only**; `apps/web`, executables, configuration, code, secrets, frozen roadmap and main are unchanged by this PR until a separately authorized merge.
- `OWNER_BASELINE_APPROVED`, `FRONTEND_IMPLEMENTED`, `E2E_CONTRACT_PASSED`, `OWNER_UI_ACCEPTED` and `LIVE_APPROVED` are all **not asserted**.
- Before any UI implementation, register the actual asset manifest, per-page approval state, domain ADR decisions and CI acceptance evidence. Future implementation uses separate governed tasks and PRs.
- Do not upgrade a REVIEW_REQUIRED screenshot into approved baseline through this registration.

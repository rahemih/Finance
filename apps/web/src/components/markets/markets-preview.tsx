import Link from "next/link";
import { FinancialIsland } from "../financial-island";
import "../../styles/markets-preview.css";

const UNKNOWN="—";
const marketHeaders=["نماد","دسته بازار","محل معامله","آخرین قیمت","تغییر ۲۴ ساعت","حجم","منبع","زمان داده"];
const watchHeaders=["ترتیب","نماد","قیمت","تغییر","منبع","آخرین به‌روزرسانی"];
const detailTabs=["نمای کلی","نمودار","تکنیکال","جریان سفارش","نقدشوندگی","کلان","اخبار","تحلیل"];

const nav=[{href:"/dashboard",label:"داشبورد"},{href:"/markets",label:"بازارها"},{href:"/markets/watchlist",label:"واچ‌لیست"},{href:"/system",label:"سلامت سامانه"},{href:"/system/alerts",label:"هشدارها"}];
function Shell({id,title,desc,children}:{id:string;title:string;desc:string;children:React.ReactNode}){
return <main dir="rtl" className="nq-mkt" data-web-p0-preview="true"><div className="nq-mkt-wrap">
<header className="nq-mkt-header"><div><strong dir="ltr">NEXUS <span>QUANT</span></strong><p>WEB-P0 · محیط نمایشی · بدون داده زنده</p></div><div className="nq-mkt-badges"><span>PREVIEW ONLY</span><span>LIVE / AUTO غیرفعال</span></div></header>
<nav aria-label="ناوبری پیش‌نمایش بازار" className="nq-mkt-nav">{nav.map(n=><Link aria-current={n.href==="/markets"&&id==="011"||n.href==="/markets/watchlist"&&id==="015"?"page":undefined} key={n.href} href={n.href}>{n.label}</Link>)}</nav>
<div className="nq-mkt-head"><div><small dir="ltr">WEB-P0 / PAGE-{id}</small><h1>{title}</h1><p>{desc}</p></div><div className="nq-mkt-asof">آخرین داده معتبر: <b>نامعلوم</b></div></div>
<div role="status" aria-live="polite" className="nq-mkt-warning"><b>!</b><span>اتصال به منبع قیمت برقرار نیست. قیمت، تغییرات، حجم و سیگنال‌ها نامعلوم‌اند؛ نمایش صفر یا اطلاعات ساختگی به‌عنوان داده واقعی ممنوع است.</span></div>
{children}<footer className="nq-mkt-footer">MOCK / REVIEW_REQUIRED · صرفاً طراحی، فاقد اتصال API و اختیار معامله · تطبیق بصری هنوز تأیید نشده است.</footer>
</div></main>}
function Panel({title,children}:{title:string;children:React.ReactNode}){return <section className="nq-mkt-panel"><h2>{title}</h2>{children}</section>}
function Empty({text}:{text:string}){return <div className="nq-mkt-empty"><b aria-hidden="true">◌</b><p>{text}</p><small>Source: UNCONNECTED · Freshness: UNKNOWN · asOf: UNKNOWN</small></div>}
function Tile({label}:{label:string}){return <article className="nq-mkt-tile"><span>{label}</span><strong><FinancialIsland>{UNKNOWN}</FinancialIsland></strong><small>داده نامعتبر یا دریافت‌نشده</small></article>}
export function MarketsPreview(){return <Shell id="011" title="نمای کلی بازارها" desc="پایش دارایی‌ها، وضعیت نشست، پوشش منابع و کیفیت داده‌ها بدون تأیید نرخ یا سیگنال">
<div className="nq-mkt-grid"><Tile label="بازارهای پوشش‌داده‌شده"/><Tile label="نشست و رژیم بازار"/><Tile label="منابع معتبر"/><Tile label="آخرین به‌روزرسانی"/></div>
<div className="nq-mkt-toolbar" role="group" aria-label="فیلترهای غیرفعال بازار">
 <label>جست‌وجوی نماد<input type="search" placeholder="اتصال داده لازم است" disabled aria-label="جست‌وجوی نماد؛ غیرفعال"/></label>
 <label>گروه بازار<select disabled aria-label="گروه بازار؛ غیرفعال"><option>همه بازارها — نامعلوم</option></select></label>
 <label>وضعیت پوشش<select disabled aria-label="پوشش منبع؛ غیرفعال"><option>نامعلوم / قطع اتصال</option></select></label>
 <Link href="/markets/watchlist" className="nq-mkt-link">مشاهده واچ‌لیست</Link>
</div>
<div className="nq-mkt-columns"><Panel title="جدول بازارها"><div className="nq-mkt-table nq-mkt-market-table" role="table" aria-label="ساختار جدول هشت ستونی بازارها؛ بدون داده معتبر"><div role="row">{marketHeaders.map(h=><span role="columnheader" key={h}>{h}</span>)}</div></div><div className="nq-mkt-mobile-label">نمای کارت دارایی‌ها · موبایل · داده نامعلوم</div><Empty text="هیچ قیمت قابل استنادی از منبع مجاز دریافت نشده است. جدول خالی به معنی نبود بازار نیست."/></Panel>
<Panel title="پوشش، منابع و تازگی"><dl className="nq-mkt-facts"><div><dt>وضعیت جریان</dt><dd>DISCONNECTED</dd></div><div><dt>تازگی مظنه</dt><dd>UNKNOWN</dd></div><div><dt>هماهنگی ارائه‌دهندگان</dt><dd>UNVERIFIED</dd></div><div><dt>پوشش نمادهای فارکس</dt><dd>NOT_MEASURED</dd></div></dl><Empty text="وضعیت منبع، تأخیر و تطبیق بین منابع در دسترس نیست."/><Link href="/system" className="nq-mkt-link">بررسی سلامت سامانه</Link></Panel></div>
</Shell>}
export function WatchlistPreview(){return <Shell id="015" title="فهرست پیگیری من" desc="دارایی‌های پین‌شده و قیمت‌های معتبر فقط پس از دریافت وضعیت کاربر و منبع">
<div className="nq-mkt-grid"><Tile label="آیتم‌های قابل تأیید"/><Tile label="آیتم‌های با داده تازه"/><Tile label="منابع متصل"/><Tile label="هشدارهای قیمت"/></div>
<div className="nq-mkt-columns"><Panel title="دارایی‌های پیگیری‌شده"><div className="nq-mkt-table nq-mkt-watch-table" role="table" aria-label="ساختار واچ‌لیست؛ وضعیت بارگذاری نامعلوم"><div role="row">{watchHeaders.map(h=><span role="columnheader" key={h}>{h}</span>)}</div></div><Empty text="واچ‌لیست کاربر بارگذاری نشده است؛ این وضعیت با «فهرست شما خالی است» متفاوت است."/></Panel>
<Panel title="جست‌وجو و تنظیمات"><label className="nq-mkt-search-label">جست‌وجو در فهرست<input type="search" disabled placeholder="بارگذاری فهرست لازم است"/></label><p className="nq-mkt-note">افزودن، حذف، مرتب‌سازی و ذخیره ترجیحات تا تأیید هویت و اتصال Backend غیرفعال است. تغییر آفلاین ذخیره‌شده محسوب نمی‌شود.</p><button type="button" disabled>افزودن دارایی — غیرفعال</button><button type="button" disabled>تغییر ترتیب — غیرفعال</button><Link href="/markets" className="nq-mkt-link">بازگشت به بازارها</Link></Panel></div>
</Shell>}
export function AssetPreview(){return <Shell id="019" title="نمای کلی دارایی" desc="جزئیات نماد، بازار و تحلیل‌ها صرفاً در حالت Fixture و بدون منبع عملیاتی">
<div className="nq-mkt-asset-id"><strong>ASSET FIXTURE: MOCK-BTCUSDT</strong><span>نماد و هویت بازار تأیید نشده است · صرفاً داده آزمایشی غیرعملیاتی</span></div>
<div className="nq-mkt-grid"><Tile label="آخرین قیمت معتبر"/><Tile label="حجم معاملات"/><Tile label="تغییرات روز"/><Tile label="کیفیت و تازگی"/></div>
<div className="nq-mkt-detail-tabs" role="group" aria-label="بخش‌های تحلیلی؛ فقط نمای کلی فعال است">{detailTabs.map((t,i)=><button key={t} type="button" disabled={i!==0} aria-current={i===0?"page":undefined}>{t}{i!==0?" · غیرفعال":""}</button>)}</div>
<div className="nq-mkt-columns"><Panel title="هویت دارایی، پوشش و رژیم بازار"><dl className="nq-mkt-facts"><div><dt>Asset ID</dt><dd>MOCK · NOT_CANONICAL</dd></div><div><dt>Market Class</dt><dd>UNKNOWN</dd></div><div><dt>Venue / Coverage</dt><dd>UNVERIFIED</dd></div><div><dt>Market Regime</dt><dd>UNKNOWN</dd></div></dl><Empty text="شناسه Fixture به رجیستری واقعی دارایی نگاشت نشده است؛ وجود دارایی واقعی تأیید نمی‌شود."/></Panel>
<Panel title="نمودار، سیگنال و شواهد"><Empty text="داده زمانی، سیگنال، شواهد و سفارش‌های بازار برای ترسیم یا تحلیل تأیید نشده‌اند."/><p className="nq-mkt-note">مسیرهای جزئیات تحلیلی و خرید/فروش غیرفعال‌اند. این صفحه توصیه معاملاتی نیست.</p><Link href="/markets" className="nq-mkt-link">بازگشت به نمای بازارها</Link></Panel></div>
</Shell>}

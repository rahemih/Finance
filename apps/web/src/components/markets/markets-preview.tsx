import Link from "next/link";
import { FinancialIsland } from "../financial-island";
import "../../styles/markets-preview.css";

const UNKNOWN="—";
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
export function MarketsPreview(){return <Shell id="011" title="نمای کلی بازارها" desc="پایش دارایی‌ها، پوشش منابع و کیفیت داده‌ها بدون تأیید نرخ یا سیگنال">
<div className="nq-mkt-grid"><Tile label="بازارهای پوشش‌داده‌شده"/><Tile label="منابع معتبر"/><Tile label="آخرین به‌روزرسانی"/><Tile label="تغییرات ۲۴ ساعته"/></div>
<div className="nq-mkt-columns"><Panel title="جدول بازارها"><div className="nq-mkt-table" role="table" aria-label="بازارها فاقد داده معتبر"><div role="row"><span role="columnheader">نماد / بازار</span><span role="columnheader">قیمت</span><span role="columnheader">تغییرات</span><span role="columnheader">کیفیت</span></div></div><Empty text="هیچ قیمت قابل استنادی از منبع مجاز دریافت نشده است."/></Panel><Panel title="پوشش و تازگی داده"><Empty text="وضعیت منبع، تأخیر و تطبیق بین منابع در دسترس نیست."/ ><Link href="/system" className="nq-mkt-link">بررسی سلامت سامانه</Link></Panel></div>
</Shell>}
export function WatchlistPreview(){return <Shell id="015" title="واچ‌لیست" desc="فهرست پیگیری دارایی‌ها با نمایش صریح نبود دسترسی و وضعیت اطلاعات">
<div className="nq-mkt-grid"><Tile label="آیتم‌های قابل تأیید"/><Tile label="هشدارهای قیمت"/><Tile label="منابع متصل"/><Tile label="آیتم‌های با داده تازه"/></div>
<div className="nq-mkt-columns"><Panel title="دارایی‌های پیگیری‌شده"><Empty text="واچ‌لیست کاربر بارگذاری نشده است؛ این حالت معادل واچ‌لیست خالی نیست."/></Panel><Panel title="فیلترها و دسترسی"><p className="nq-mkt-note">جست‌وجو، افزودن و حذف دارایی تا تأیید احراز هویت و اتصال سرویس غیرفعال‌اند.</p><button type="button" disabled>افزودن دارایی — غیرفعال</button><Link href="/markets" className="nq-mkt-link">بازگشت به بازارها</Link></Panel></div>
</Shell>}
export function AssetPreview(){return <Shell id="019" title="نمای کلی دارایی" desc="جزئیات نماد و بازار فقط پس از شناسایی معتبر دارایی و تأیید منبع نمایش داده می‌شوند">
<div className="nq-mkt-grid"><Tile label="قیمت مرجع"/><Tile label="حجم معاملات"/><Tile label="تغییرات روز"/><Tile label="کیفیت و تازگی"/></div>
<div className="nq-mkt-columns"><Panel title="هویت دارایی و بازار"><Empty text="شناسه دارایی در وضعیت پیش‌نمایش به منبع معتبر نگاشت نشده است."/ ><p className="nq-mkt-note">Asset ID و Market ID باید مستقل از عنوان قابل مشاهده توسط Backend اعتبارسنجی شوند.</p></Panel><Panel title="نمودار و عمق بازار"><Empty text="داده زمانی و سفارش‌های بازار برای ترسیم نمودار تأیید نشده‌اند."/ ><p className="nq-mkt-note">هیچ سفارش، سیگنال یا مسیر معامله از این صفحه فعال نیست.</p><Link href="/markets" className="nq-mkt-link">بازگشت به نمای بازارها</Link></Panel></div>
</Shell>}

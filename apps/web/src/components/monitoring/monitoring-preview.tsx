import Link from "next/link";
import { FinancialIsland } from "../financial-island";
import { MONITORING_ROUTES, UNKNOWN_DATA_MARKER } from "../../lib/monitoring-preview-contract";
import "../../styles/monitoring-preview.css";
type StatusTone = "warning" | "muted" | "critical";
function Tag({ children, tone="warning" }: {children: React.ReactNode; tone?: StatusTone}) {
  return <span className={`nq-mon-tag nq-mon-tag--${tone}`}>{children}</span>;
}
function Tile({ label, details }: {label: string; details: string}) {
  return <article className="nq-mon-tile"><div className="nq-mon-tile__top"><span>{label}</span><Tag tone="muted">فاقد اتصال</Tag></div><strong><FinancialIsland>{UNKNOWN_DATA_MARKER}</FinancialIsland></strong><small>{details}</small></article>;
}
function Box({ title, detail, children, className="" }: {title:string;detail?:string;children:React.ReactNode;className?:string}) {
  return <section className={`nq-mon-panel ${className}`} aria-label={title}><div className="nq-mon-panel__heading"><h2>{title}</h2>{detail?<span>{detail}</span>:null}</div>{children}</section>;
}
function Notice({ kind }: {kind:"risk"|"health"|"alerts"}) {
  const copy=kind==="risk"?"وضعیت ریسک تأیید نشده است؛ هیچ معامله‌ای مجاز نیست.":kind==="health"?"وضعیت سلامت سامانه نامعلوم است؛ نمی‌توان آن را سالم فرض کرد.":"به سرویس هشدار متصل نیستیم؛ تعداد هشدارهای واقعی نامعلوم است.";
  return <div className="nq-mon-critical" role="status" aria-live="polite"><span aria-hidden="true">!</span><p>{copy}</p><Tag tone="critical">نیازمند منبع معتبر</Tag></div>;
}
function Shell({active,title,summary,children}:{active:"010"|"079"|"084";title:string;summary:string;children:React.ReactNode}){
  return <main className="nq-mon" dir="rtl" data-web-p0-preview="true"><div className="nq-mon-wrap">
    <header className="nq-mon-header"><div><div className="nq-mon-logo" dir="ltr">NEXUS <span>QUANT</span></div><p>محیط نمایشی غیرعملیاتی · بدون داده زنده</p></div><div className="nq-mon-header__right"><Tag tone="warning">PREVIEW ONLY</Tag><Tag tone="critical">LIVE / AUTO غیرفعال</Tag></div></header>
    <nav className="nq-mon-nav" aria-label="بخش‌های پیش‌نمایش">{MONITORING_ROUTES.map(x=><Link key={x.id} href={x.href} aria-current={x.id===active?"page":undefined} className={x.id===active?"nq-mon-link is-active":"nq-mon-link"}>{x.label}</Link>)}</nav>
    <div className="nq-mon-heading"><div><p className="nq-mon-kicker">WEB-P0 / PAGE-{active}</p><h1>{title}</h1><p>{summary}</p></div><div className="nq-mon-proof"><span>آخرین داده معتبر:</span><strong>در دسترس نیست</strong></div></div>
    {children}
    <footer className="nq-mon-footer"><span>طراحی مرجع توسط مالک تأیید شده · تطبیق مرورگری و هش تصاویر هنوز انجام نشده است.</span><span dir="ltr">© NEXUS QUANT • SOURCE DRAFT</span></footer>
  </div></main>;
}
function Empty({children}:{children:React.ReactNode}){return <div className="nq-mon-empty"><span aria-hidden="true" className="nq-mon-empty__icon">◌</span><p>{children}</p><small>بدون اتصال به API، هیچ مقدار یا رخدادی تأیید نمی‌شود.</small></div>}
export function DashboardPreview(){
 return <Shell active="010" title="داشبورد" summary="نمای کلی بازار، فرصت‌ها، وضعیت ریسک و سلامت سامانه"><Notice kind="risk"/>
  <div className="nq-mon-tiles"><Tile label="ارزش پرتفوی" details="موجودی به سرویس متصل نیست"/><Tile label="فرصت‌های قابل بررسی" details="نتایج اسکنر تأیید نشده"/><Tile label="وضعیت بازار" details="Regime و منبع داده نامشخص"/><Tile label="حساب‌های دمو" details="اطلاعات حسابی بارگذاری نشده"/></div>
  <div className="nq-mon-duo"><Box title="نمای کلی بازار" detail="PAGE-011"><Empty>قیمت، حجم و تغییرات بازار در دسترس نیستند.</Empty><Link className="nq-mon-soft-link" href="/system">بررسی وضعیت سامانه</Link></Box>
   <Box title="وضعیت ریسک و فرصت‌ها" detail="فقط مشاهده"><Empty>سیگنال معتبر یا سطح ریسک قابل نمایش نیست.</Empty><p className="nq-mon-disclaimer">Risk Veto مستقل است و از این صفحه قابل تغییر نیست.</p></Box></div>
  <div className="nq-mon-duo"><Box title="سلامت سامانه" detail="منبع: P22"><Empty>Heartbeat و وضعیت سرویس‌ها نامشخص است.</Empty><Link href="/system" className="nq-mon-soft-link">صفحه سلامت سامانه</Link></Box><Box title="هشدارها" detail="ممکن است هشدار واقعی وجود داشته باشد"><Empty>به مرکز اعلان‌ها اتصال برقرار نیست.</Empty><Link href="/system/alerts" className="nq-mon-soft-link">مرکز هشدارها</Link></Box></div>
 </Shell>
}
export function SystemHealthPreview(){
return <Shell active="079" title="سلامت سامانه" summary="پایش وضعیت سرویس‌ها، منابع داده، Heartbeat و شواهد عملیاتی">
  <Notice kind="health"/><div className="nq-mon-tiles"><Tile label="حالت عملیاتی" details="NORMAL / DEGRADED / HALTED: نامعلوم"/><Tile label="آخرین Heartbeat" details="زمانی دریافت نشده"/><Tile label="وضعیت ارائه‌دهندگان" details="اتصال و پوشش اندازه‌گیری نشده"/><Tile label="کیفیت داده‌ها" details="SLO و تأخیر نامشخص"/></div>
  <div className="nq-mon-duo"><Box title="سرویس‌های پایش‌شده" detail="فهرست وضعیت"><ul className="nq-mon-service-list">{["Market Data","Risk Veto (A5)","Pre-Trade Firewall (P16)","Notification Engine"].map(s=><li key={s}><FinancialIsland>{s}</FinancialIsland><Tag tone="muted">نامشخص</Tag></li>)}</ul><p className="nq-mon-disclaimer">موارد بالا عنوان سرویس‌های قراردادی‌اند، نه تأیید وجود نمونه عملیاتی.</p></Box>
  <Box title="رخدادها و شواهد" detail="Read-only"><Empty>شناسه رخداد، زمان و شواهد معتبر هنوز دریافت نشده‌اند.</Empty><Link className="nq-mon-soft-link" href="/system/alerts">بررسی اعلان‌ها</Link></Box></div>
</Shell>;
}
export function AlertsPreview(){
return <Shell active="084" title="مرکز هشدارها" summary="نمایش اعلان‌ها، اولویت‌ها و وضعیت ارجاع بدون امکان تغییر یا تأیید رخداد"><Notice kind="alerts"/>
  <div className="nq-mon-info-strip" role="note"><span>بحرانی</span><span>مهم</span><span>اطلاع‌رسانی</span><strong>فیلترها در حالت پیش‌نمایش غیرفعال‌اند.</strong></div>
  <div className="nq-mon-duo nq-mon-duo--alerts"><Box title="فهرست اعلان‌ها" detail="به سرور متصل نیست"><Empty>هیچ فهرستی دریافت نشده؛ این به معنی صفر بودن هشدارهای واقعی نیست.</Empty></Box><Box title="جزئیات و سوابق ارجاع" detail="اطلاعات معتبر مورد نیاز"><Empty>اعلان انتخاب‌شده، زمان رخداد و شناسه منبع در دسترس نیست.</Empty><p className="nq-mon-disclaimer">خوانده‌شدن اعلان، حل Incident یا حذف وتوی ریسک محسوب نمی‌شود.</p></Box></div>
</Shell>;
}

import Link from "next/link";
import "../../styles/markets-reference-preview.css";

/**
 * Owner-approved visual source: Google Docs NEXUS QUANT Web Runtime v0.8.
 * Reference screenshot IDs: 011-01..06, 015-01..05, 019-01..06.
 * All prices, bars, timeline, symbols and health labels below are SYNTHETIC
 * display fixtures. Nothing is fetched and there is no trade authority.
 */
const quotes=[
  {symbol:"BTC/USD",venue:"Crypto",source:"Sample-C1",price:"67,840.20",change:"+1.26%",volume:"2.4B",time:"14:20",status:"FRESH"},
  {symbol:"ETH/USD",venue:"Crypto",source:"Sample-C2",price:"3,428.10",change:"+0.83%",volume:"998M",time:"14:20",status:"FRESH"},
  {symbol:"EUR/USD",venue:"Forex",source:"Sample-FX1",price:"1.08142",change:"−0.14%",volume:"—",time:"14:19",status:"FRESH"},
  {symbol:"XAU/USD",venue:"Context",source:"Sample-CTX",price:"—",change:"—",volume:"—",time:"—",status:"NO COVERAGE"},
  {symbol:"SOL/USD",venue:"Crypto",source:"Sample-C1",price:"178.40",change:"+2.81%",volume:"312M",time:"14:20",status:"FRESH"},
  {symbol:"GBP/USD",venue:"Forex",source:"Sample-FX1",price:"1.29610",change:"−0.22%",volume:"—",time:"14:19",status:"FRESH"}
] as const;
const watch=[quotes[0],quotes[1],quotes[2],quotes[4]];
const nav=[
 {label:"داشبورد",href:"/dashboard",icon:"▤"},
 {label:"بازار و تحلیل",href:"/markets",icon:"◇"},
 {label:"فرصت‌ها و سیگنال‌ها",href:"/markets/watchlist",icon:"♧"},
 {label:"پرتفوی و ریسک",href:"/dashboard",icon:"◇"},
 {label:"مرکز دمو",href:"/dashboard",icon:"▣"},
 {label:"سلامت سامانه",href:"/system",icon:"⚑"},
 {label:"اعلان‌ها",href:"/system/alerts",icon:"☷"},
 {label:"کاربران و دسترسی‌ها",href:"/system",icon:"♧"}
];
function Pill({children,tone="blue"}:{children:React.ReactNode;tone?:"blue"|"gold"|"green"|"red"}){
return <span className={"nqr-pill nqr-"+tone}>{children}</span>;
}
function Badge({children}:{children:React.ReactNode}){return <span className="nqr-crumb-badge">{children}</span>}
function Frame({id,title,crumb,subtitle,action,children}:{id:"011"|"015"|"019";title:string;crumb:string;subtitle:string;action:string;children:React.ReactNode}){
return <div className="nqr-frame" data-web-p0-preview="true" data-reference-screenshot={"PAGE-"+id} dir="rtl">
<header className="nqr-topbar">
 <div className="nqr-top-actions"><Pill>حساب نمایشی</Pill><Pill tone="gold">DEMO · MOCK</Pill><Pill>فارسی</Pill></div>
 <div className="nqr-top-search" role="search">⌕　جست‌وجو در سامانه</div>
 <div className="nqr-brand" dir="ltr"><strong><em>N</em> NEXUS QUANT</strong><small>Intelligent Trading Platform</small></div>
</header>
<div className="nqr-body">
 <aside className="nqr-sidebar" aria-label="ناوبری اصلی پروژه"><small>پایش و تصمیم‌یار</small>
 {nav.slice(0,7).map(n=><Link className={n.label==="بازار و تحلیل"?"nqr-side-link nqr-side-active":"nqr-side-link"} key={n.label} href={n.href}><span>{n.icon}</span>{n.label}</Link>)}
 <small>امنیت و کنترل</small><Link className="nqr-side-link" href="/system"><span>♧</span>کاربران و دسترسی‌ها</Link>
 </aside>
 <main className="nqr-main">
 <div className="nqr-page-top"><div className="nqr-page-title"><p className="nqr-kicker">{crumb}</p><h1>{title}</h1><p className="nqr-page-subtitle">{subtitle}</p></div>
 <div className="nqr-actions"><button type="button" disabled>{action}</button><Badge>MOCK DATA · NOT LIVE</Badge></div></div>
 <div className="nqr-green-banner" role="status"><span className="nqr-checked">✓</span><div><strong>{id==="011"?"نمای نمونه بازارها آماده نمایش است":id==="015"?"فهرست پیگیری آزمایشی فعال است":"نمایش اطلاعات آزمایشی دارایی"}</strong><small>تمام قیمت‌ها، نمودارها و وضعیت‌ها صرفاً Fixture نمایشی‌اند؛ سفارش، منبع واقعی یا ریسک ایجاد نمی‌شود.</small></div><Pill tone="gold">MOCK / DESIGN</Pill></div>
 {children}
 <footer className="nqr-content-foot"><span>فقط برای بازبینی UI/UX؛ نمونه‌ها اطلاعات واقعی یا مجوز معامله نیستند.</span><span dir="ltr">NEXUS QUANT　•　v0.8 DESIGN DRAFT</span></footer>
 </main>
</div>
</div>;
}
function Stat({label,value,note}:{label:string;value:string;note:string}){return <section className="nqr-stat"><span>{label}</span><b dir="ltr">{value}</b><small>{note}</small></section>}
function Stats({items}:{items:[string,string,string][]}){return <div className="nqr-stats">{items.map(([label,value,note])=><Stat key={label} label={label} value={value} note={note}/>)}</div>}
function Card({title,tag,children}:{title:string;tag?:string;children:React.ReactNode}){return <section className="nqr-card"><header className="nqr-card-header"><h2>{title}</h2>{tag&&<Pill>{tag}</Pill>}</header>{children}</section>}
function QuoteStatus({status}:{status:string}){return <Pill tone={status==="FRESH"?"green":"red"}>{status}</Pill>}
function PriceTable({items,isWatch=false}:{items:readonly typeof quotes[number][];isWatch?:boolean}){return <>
 <div className="nqr-table-scroll"><table className="nqr-table"><thead><tr>{isWatch?<><th>نماد</th><th>بازار</th><th>آخرین قیمت</th><th>تغییر</th><th>کیفیت</th><th>زمان</th><th>جزئیات</th></>:<><th>دارایی / بازار</th><th>آخرین قیمت</th><th>تغییر</th><th>حجم</th><th>زمان نمونه</th><th>کیفیت</th><th>منبع نمونه</th><th>مسیر</th></>}</tr></thead><tbody>
 {items.map(q=><tr key={q.symbol}><td className="nqr-symbol"><b dir="ltr">{isWatch?"★ ":""}{q.symbol}</b><small>{q.venue}</small></td>
 {isWatch?<td>{q.venue}</td>:null}<td dir="ltr">{q.price}</td><td dir="ltr">{q.change}</td>{!isWatch&&<td dir="ltr">{q.volume}</td>}
 <td>{isWatch?<QuoteStatus status={q.status}/>:<span dir="ltr">{q.time}</span>}</td>
 <td>{isWatch?<span dir="ltr">{q.time}</span>:<QuoteStatus status={q.status}/>}</td>
 {!isWatch&&<td>{q.source}</td>}
 <td><Link href="/markets/mock-btcusdt" className="nqr-mini-action">جزئیات</Link></td></tr>)}
 </tbody></table></div>
 <div className="nqr-mobile-quotes">{items.map(q=><article className="nqr-quote-card" key={q.symbol}><div className="nqr-quote-head"><div><strong dir="ltr">{isWatch?"★ ":""}{q.symbol}</strong><p>{q.venue} · {q.source}</p></div><div className="nqr-quote-num"><b dir="ltr">{q.price}</b><small>MOCK · {q.time}</small></div></div><div className="nqr-quote-foot"><QuoteStatus status={q.status}/><span dir="ltr">{q.change}</span></div></article>)}</div>
 </>}
function MiniBars(){return <div className="nqr-bars" aria-label="نمودار ستونی مصنوعی، صرفاً تزئینی">{[36,51,40,33,47,43,54,37,46,29,51,34,37,26].map((h,i)=><span key={i} style={{height:h}}/>)}</div>}
function RefNotice({children}:{children:React.ReactNode}){return <div className="nqr-foot-notice">{children}</div>}
export function MarketsReferencePreview(){return <Frame id="011" title="نمای کلی بازارها" crumb="بازار و تحلیل / نمونه طراحی غیرعملیاتی" subtitle="وضعیت قیمت‌ها، پوشش بازار و کیفیت داده — فقط مشاهده؛ هیچ دستور معاملاتی وجود ندارد." action="↻ تازه‌سازی">
 <Stats items={[["تعداد دارایی‌های نمونه","6","Fixture only"],["نماد با داده تازه نمونه","4","همراه زمان و منبع"],["Market Regime","UNKNOWN","بدون طبقه‌بندی معتبر"],["محیط نمایش","DEMO","NOT LIVE"]]}/>
 <div className="nqr-toolbar"><input aria-label="جست‌وجوی نماد در پیش‌نمایش" placeholder="⌕　 جست‌وجوی نماد یا بازار..." disabled/><div className="nqr-toolbar-buttons"><button type="button" className="nqr-current" disabled>همه بازارها</button><button type="button" disabled>Crypto</button><button type="button" disabled>Forex</button><button type="button" disabled>Context</button><Link href="/markets/watchlist">فهرست پیگیری</Link></div></div>
 <div className="nqr-columns"><Card title="فهرست نمادها و قیمت‌های نمونه" tag="MOCK ONLY"><PriceTable items={quotes}/><p className="nqr-card-foot">داده ناقص یا — به معنای نمایش داده نمی‌شود؛ نمایش خالی به معنی دریافت داده واقعی نیست.</p></Card>
 <div className="nqr-side-panels"><Card title="پوشش منابع و وضعیت کیفیت" tag="SOURCE FIXTURE"><div className="nqr-source-list">{[["Crypto","FRESH"],["Forex","FRESH"],["Context","NO COVERAGE"],["Stream","MOCK"]].map(([name,status])=><div key={name}><span dir="ltr">{name}</span><Pill tone={status==="FRESH"?"green":status==="MOCK"?"gold":"red"}>{status}</Pill></div>)}</div></Card>
 <Card title="پراکندگی بازار · داده ساختگی"><MiniBars/><p className="nqr-muted">Visualization fixture؛ نه شاخص مالی معتبر</p></Card></div></div>
 <div className="nqr-bottom-row"><RefNotice><b>تازگی داده</b><br/>برچسب FRESH / STALE / UNKNOWN با زمان و منبع</RefNotice><RefNotice><b>محدوده Forex</b><br/>عمق سفارش جهانی فرض نشده؛ پوشش وابسته به Provider</RefNotice><RefNotice><b>مرز اختیار</b><br/>داده این مرکز مرجع اجرای معامله یا توصیه خودکار نیست.</RefNotice></div>
 </Frame>}
export function WatchlistReferencePreview(){return <Frame id="015" title="فهرست پیگیری من" crumb="بازار و تحلیل / Watchlist / نمونه طراحی غیرعملیاتی" subtitle="دارایی‌های پین‌شده برای مشاهده سریع — افزودن یا حذف اینجا سفارش معاملاتی نیست." action="+ افزودن دارایی">
 <Stats items={[["دارایی‌های پین‌شده نمونه","4","Preview صرفاً"],["قیمت‌های معتبر نمونه","4","Fixture time"],["ثبت تغییر در سرور","NOT CONNECTED","API proposed"],["محیط","DEMO","NOT LIVE"]]}/>
 <div className="nqr-toolbar"><input aria-label="جست‌وجوی فهرست پیگیری" placeholder="⌕　 جست‌وجو در فهرست پیگیری..." disabled/><div className="nqr-toolbar-buttons"><button type="button" disabled className="nqr-current">ترتیب پین‌شده</button><button type="button" disabled>بر اساس نام</button><button type="button" disabled>افزودن دارایی</button></div></div>
 <div className="nqr-columns"><Card title="دارایی‌های منتخب" tag="MOCK · READ ONLY"><PriceTable items={watch} isWatch/><p className="nqr-card-foot">در تغییرات واقعی افزودن، حذف و تغییر ترتیب، پس از تأیید سرور و قابل برگشت می‌شوند.</p></Card>
 <div className="nqr-side-panels"><Card title="مدیریت پیگیری" tag="READ / REQUEST"><div className="nqr-source-list">{[["افزودن دارایی","بازکردن انتخابگر"],["مرتب‌سازی","درخواست ترجیحات"],["حذف از فهرست","تأیید و Rollback"],["آخرین به‌روزرسانی","MOCK · 14:20"]].map(([name,status])=><div key={name}><span>{name}</span><span>{status}</span></div>)}</div></Card><div className="nqr-yellow-notice">این صفحه نه پوزیشن می‌سازد، نه مبلغی تخصیص می‌دهد و نه سفارش خرید/فروش ارسال می‌کند.</div></div></div>
 </Frame>}
function Trend(){const poly="0,168 16,163 30,166 46,157 64,145 78,151 96,138 113,143 132,128 150,120 168,128 190,138 209,126 228,113 244,98 266,92 282,84 296,96 312,88 331,69 350,72 369,61 390,73 407,60 425,47 440,59 457,46 474,40 490,52 506,35 524,44 539,28 555,35 572,19 590,27 607,15 623,20 640,8";return <div className="nqr-chart" aria-label="نمودار خطی مصنوعی هفت روزه؛ نمایشی و غیرواقعی"><div className="nqr-chart-label">SYNTHETIC · 7D</div><svg viewBox="0 0 680 215" role="img" aria-label="خط روند ساختگی رو به بالا"><g stroke="#24516f" strokeDasharray="3 5" strokeWidth="1"><line x1="20" y1="40" x2="660" y2="40"/><line x1="20" y1="80" x2="660" y2="80"/><line x1="20" y1="120" x2="660" y2="120"/><line x1="20" y1="160" x2="660" y2="160"/></g><polyline points={poly} transform="translate(20 18)" fill="none" stroke="#38c4ff" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"/></svg><p>این سری ساختگی است و برای بررسی چیدمان نمودار طراحی شده؛ هیچ منبع زنده‌ای متصل نیست.</p></div>}
export function AssetReferencePreview(){return <Frame id="019" title="جزئیات دارایی" crumb="بازارها / Crypto / BTC / Design fixture" subtitle="مرجع بصری Asset Overview؛ قیمت‌ها، تحلیل‌ها و Providerها صرفاً نمونه آزمایشی هستند." action="☆ افزودن به فهرست">
 <div className="nqr-asset-hero"><div><span>ASSET ID · BTC-USD-SAMPLE</span><h2 dir="ltr">BTC / USD</h2><p>رمزارز · Sample venue C1 · Asset Registry Fixture</p></div><div className="nqr-asset-price"><b dir="ltr">67,840.20</b><small dir="ltr">+1.26% · 14:20 · MOCK</small></div></div>
 <div className="nqr-tabs">{["نمای کلی","نمودار","تحلیل تکنیکال","جریان سفارش","نقدشوندگی","بنیادی","اخبار","تحلیل هوشمند"].map((n,i)=><button key={n} type="button" disabled className={i===0?"nqr-current":""}>{n}</button>)}</div>
 <Stats items={[["آخرین قیمت نمونه","67,840.20","USD · Fixture"],["کیفیت قیمت","MOCK / FRESH","Source verified: NO"],["بازه تغییر","+1.26%","MOCK · 24h"],["محیط","DEMO","NOT LIVE"]]}/>
 <div className="nqr-columns nqr-asset-columns"><Card title="روند قیمت نمونه" tag="SYNTHETIC · 7D"><Trend/></Card><div className="nqr-side-panels"><Card title="اطلاعات دارایی" tag="READ ONLY"><div className="nqr-source-list">{[["شناسه","BTC-USD-SAMPLE"],["کلاس بازار","Crypto"],["محل قیمت‌گذاری","Sample-C1"],["کیفیت","MOCK / FRESH"],["منبع معتبر","NOT CONNECTED"],["آخرین بروزرسانی","14:20 MOCK"]].map(([name,v])=><div key={name}><span>{name}</span><span dir="ltr">{v}</span></div>)}</div></Card><Card title="سیگنال‌ها و شواهد"><p className="nqr-card-description">خروجی مدل و Signal واقعی موجود نیست؛ وضعیت تحلیل صرفاً نمایشی است.</p><Pill tone="gold">NO VERIFIED SIGNAL</Pill></Card></div></div>
 <RefNotice>نمای کلی دارایی فقط Read و ناوبری است؛ Watchlist صرفاً ترجیحات. هیچ Order، Signal یا Risk-Veto از اینجا ایجاد یا تغییر داده نمی‌شود.</RefNotice>
 </Frame>}

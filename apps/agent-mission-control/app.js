'use strict';
// NEXUS QUANT Mission Control — public GitHub evidence only.
// No credentials, order API, process control, or assumed agent execution.
const REPO = 'rahemih/Finance';
const API = `https://api.github.com/repos/${REPO}`;
const WEB = `https://github.com/${REPO}`;
const REFRESH_MS = 300_000; // Conservative unauthenticated public GitHub API budget.
const AGENTS = [
 ['A0','هماهنگ‌کننده مرکزی','مدیریت وظایف و مسیر کار'],
 ['A1','معماری و مهندسی','طراحی سیستم و کدنویسی'],
 ['A2','داده','منابع و کیفیت داده'],
 ['A3','هوش بازار','تحلیل بازار و رویدادها'],
 ['A4','تحلیل کمی','مدل‌ها و بک‌تست'],
 ['A5','ریسک','کنترل مستقل و حق وتو'],
 ['A6','اجرا','OMS و اجرای آزمایشی'],
 ['A7','یادگیری','آموزش و اعتبارسنجی'],
 ['A8','امنیت','ممیزی و حق وتو'],
 ['A9','عملیات','زیرساخت و بازیابی'],
 ['A10','مستندسازی','شواهد و بررسی نهایی']
];
// Verified historical snapshot, not a claim of current live status.
const SNAPSHOT = Object.freeze({
 captured_at:'2026-11-17T08:34:00Z',
 runs:[
  {id:44047624654,name:'Finance Agent Read-Only Watch',status:'completed',conclusion:'success',event:'pull_request',head_sha:'69b316c86a5d5041f12273e2c46f8c53432353ce',created_at:'2026-11-17T08:32:31Z'},
  {id:44047624535,name:'Governance Verify',status:'completed',conclusion:'success',event:'pull_request',head_sha:'69b316c86a5d5041f12273e2c46f8c53432353ce',created_at:'2026-11-17T08:32:31Z'},
  {id:44018013026,name:'P18 Demo Learning Runtime',status:'completed',conclusion:'success',event:'schedule',head_sha:'9c26afc90c0415f5cf2e3ddc4f2f9cd8bb42d2fe'},
  {id:43843575325,name:'Branch Hygiene',status:'completed',conclusion:'failure',event:'schedule',head_sha:'9c26afc90c0415f5cf2e3ddc4f2f9cd8bb42d2fe'}
 ],
 prs:[
  {number:532,title:'Governed autonomous-builder bootstrap + read-only scheduled watch',draft:true,updated_at:'2026-11-17T08:32:31Z'},
  {number:504,title:'Next.js build — blocked on SBOM license review',draft:true},
  {number:505,title:'Independent dependency license review pending',draft:true},
  {number:512,title:'PAGE-001 login visual and Chromium evidence'},
  {number:509,title:'Read-only market, watchlist and asset previews'},
  {number:529,title:'P24 account and credential readiness evidence'},
  {number:525,title:'Provider approval xChief and Toobit'},
  {number:524,title:'P24 eligibility research'},
  {number:523,title:'P24-C non-live preflight'},
  {number:507,title:'P0-B dashboard and 212 design references'},
  {number:497,title:'WEB-P0 Next.js foundation'},
  {number:498,title:'Login preview without session'}
 ],
 issues:[
  {number:531,title:'FIN-P24-WZ-001 — Governed Autonomous Builder & watch'},
  {number:530,title:'WEB-P0 independent license review and SBOM blocker'},
  {number:528,title:'P24-B official prerequisite checklist'},
  {number:508,title:'P24-DEMO independent acceptance tracker'},
  {number:491,title:'P24 pre-first-live tracking (blocked)'},
  {number:527,title:'Branch hygiene stale/excess branches'}
 ]
});
const state = {
 runs:SNAPSHOT.runs, prs:SNAPSHOT.prs, issues:SNAPSHOT.issues,
 source:'snapshot', lastVerified:null, error:null,
 selectedRun:null, selectedPR:null, currentFilter:'all', jobs:[], loadedJobsFor:null,
 latestRequest:0, isLoading:false, jobRequest:0, filesRequest:0
};
const $ = id=>document.getElementById(id);
const escapeHtml = value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const validId = n=>Number.isSafeInteger(Number(n))&&Number(n)>0?Number(n):null;
const runUrl = n=>`${WEB}/actions/runs/${validId(n) || 0}`;
const prUrl = n=>`${WEB}/pull/${validId(n) || 0}`;
const issueUrl = n=>`${WEB}/issues/${validId(n) || 0}`;
const hash = s=>/^[0-9a-f]{40}$/.test(String(s||''))?String(s).slice(0,9):'—';
function formatDate(d){try{if(!d)return '—';const date=new Date(d);if(Number.isNaN(date.getTime()))return '—';return new Intl.DateTimeFormat('fa-IR',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(date)}catch{return '—'}}
function clock(){ $('clock').textContent=new Intl.DateTimeFormat('fa-IR',{hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date()); }
function jobStatus(run){if(run.status!=='completed')return 'active';if(run.conclusion==='success')return 'success';if(['failure','timed_out','startup_failure','action_required'].includes(run.conclusion))return 'failure';return 'other'}
function stateLabel(s){return ({active:'در حال اجرا',success:'موفق',failure:'ناموفق',other:'متوقف/نامعلوم'})[s]}
function statusSymbol(s){return ({active:'◉',success:'✓',failure:'!',other:'—'})[s]}
function renderStats(){const active=state.runs.filter(r=>jobStatus(r)==='active').length;const failed=state.runs.filter(r=>jobStatus(r)==='failure').length;$('stat-active').textContent=String(active);$('stat-failed').textContent=String(failed);$('stat-prs').textContent=String(state.prs.length);$('stat-issues').textContent=String(state.issues.length)}
function renderAgents(){ $('agent-grid').innerHTML=AGENTS.map(([id,name,description])=>{ const info=window.nexusAgentTrace?.lastForAgent(id);const label=info?.label||'فعالیت مستقل تأیید نشده';return `<article class="agent-card" aria-label="${escapeHtml(id)} ${escapeHtml(name)} — ${escapeHtml(label)}"><span class="agent-meta">${escapeHtml(id)}</span><div class="agent-head"><span class="agent-id">${escapeHtml(id)}</span><span><span class="agent-name">${escapeHtml(name)}</span><span class="agent-sub">${escapeHtml(description)}</span></span></div><div class="agent-foot"><span class="agent-status-dot"></span><span>${escapeHtml(label)}</span></div></article>`}).join('') }
function renderRuns(){let runs=state.runs;if(state.currentFilter==='active')runs=runs.filter(x=>jobStatus(x)==='active');if(state.currentFilter==='failed')runs=runs.filter(x=>jobStatus(x)==='failure');$('run-list').innerHTML=runs.length?runs.map(run=>{
 const s=jobStatus(run);const selected=state.selectedRun===run.id;
 return `<button type="button" class="run-item ${selected?'selected':''}" data-run="${validId(run.id)||0}" aria-pressed="${selected}"><span class="run-dot ${s}">${statusSymbol(s)}</span><span class="run-content"><span class="run-title">${escapeHtml(run.name||'Workflow بدون نام')}</span><span class="run-meta"><span>#${escapeHtml(run.id)}</span><span>${escapeHtml(run.event||'—')}</span><span>${escapeHtml(formatDate(run.created_at))}</span><span class="ltr">${escapeHtml(hash(run.head_sha))}</span></span></span><span class="run-state ${s}">${stateLabel(s)}</span></button>`
 }).join(''):'<div class="empty-state">برای این فیلتر اجرای ثبت‌شده‌ای وجود ندارد.</div>';
 $('run-list').querySelectorAll('[data-run]').forEach(btn=>btn.addEventListener('click',()=>selectRun(Number(btn.dataset.run)))); }
function renderPRs(){$('pr-list').innerHTML=state.prs.length?state.prs.slice(0,24).map(pr=>`<button type="button" class="pr-item" data-pr="${validId(pr.number)||0}"><div class="pr-title">${escapeHtml(pr.title||'PR بدون عنوان')}</div><div class="pr-sub"><span class="ltr">PR #${escapeHtml(pr.number)}</span><span class="tiny-tag ${pr.draft?'warn':''}">${pr.draft?'DRAFT':'OPEN'}</span><span>${escapeHtml(formatDate(pr.updated_at))}</span><span>مشاهده فایل‌ها ↗</span></div></button>`).join(''):'<div class="empty-state">در داده‌های فعلی PR بازی ثبت نشده است.</div>';
 $('pr-list').querySelectorAll('[data-pr]').forEach(btn=>btn.addEventListener('click',()=>selectPR(Number(btn.dataset.pr)))); }
function renderIssues(){const failures=state.runs.filter(x=>jobStatus(x)==='failure').slice(0,3).map(r=>`<article class="issue-item"><div class="issue-title"><a href="${runUrl(r.id)}" target="_blank" rel="noopener noreferrer">⛔ اجرای ناموفق: ${escapeHtml(r.name)}</a></div><div class="issue-sub"><span>Workflow</span><span>${escapeHtml(formatDate(r.created_at))}</span><span class="ltr">#${escapeHtml(r.id)}</span></div></article>`);
 const issues=state.issues.slice(0,16).map(i=>`<article class="issue-item"><div class="issue-title"><a href="${issueUrl(i.number)}" target="_blank" rel="noopener noreferrer">${escapeHtml(i.title)}</a></div><div class="issue-sub"><span class="tiny-tag warn">OPEN ISSUE</span><span class="ltr">#${escapeHtml(i.number)}</span><span>${escapeHtml(formatDate(i.updated_at))}</span></div></article>`);
 $('issue-list').innerHTML=[...failures,...issues].join('')||'<div class="empty-state">باگ یا Issue باز ثبت‌شده‌ای دیده نشد.</div>';}
function renderSource(){let text,led;
 if(state.source==='live'){text=`داده GitHub دریافت شد · ${formatDate(state.lastVerified)}`;led='good';$('freshness').textContent=`● اتصال واقعی · آخرین واکشی ${formatDate(state.lastVerified)}`;$('truth-text').textContent='اطلاعات Workflowها، PRها و Issueها از GitHub عمومی خوانده شده‌اند. وضعیت A0 تا A10 تا زمان اتصال تله‌متری اجرای مستقل، ناشناخته است. این صفحه فقط مشاهده می‌کند، نه کدنویسی یا معامله.';}
 else{text='آخرین نمونه تاریخ‌دار · ارتباط زنده برقرار نیست';led='amber';$('freshness').textContent=`◌ نمای داده تاریخی ${formatDate(SNAPSHOT.captured_at)}`;$('truth-text').textContent='اخطار: اکنون داده‌های تاریخ‌دار ۱۷ نوامبر ۲۰۲۶ نمایش داده می‌شوند و وضعیت فعلی را ثابت نمی‌کنند. برای مشاهده واقعی، اتصال به api.github.com لازم است. هیچ ایجنتی بدون تله‌متری «فعال» فرض نمی‌شود.';}
 $('github-source').textContent=text;$('github-led').className='source-led '+led;
 if(state.error){$('freshness').title=state.error;$('truth-banner').style.borderColor='#77464a';}else{$('truth-banner').style.borderColor='';$('freshness').title='';}
 $('footer-meta').textContent=state.source==='live'?'داده GitHub تأییدشده · بدون دسترسی نوشتن · واکشی هر ۵ دقیقه':'حالت داده تاریخی · بدون تأیید وضعیت لحظه‌ای';}
function render(){renderStats();renderSource();renderRuns();renderPRs();renderIssues()}
async function api(path){const ctrl=new AbortController();const timeout=setTimeout(()=>ctrl.abort(),13000);try{
 const response=await fetch(`${API}${path}`,{headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},signal:ctrl.signal,cache:'no-store'});
 if(!response.ok){const remain=response.headers.get('x-ratelimit-remaining');const msg=response.status===403||response.status===429?'سهمیه GitHub یا دسترسی API محدود شده':`پاسخ GitHub: ${response.status}`;throw new Error(remain==='0'?'سهمیه عمومی GitHub API به پایان رسیده':msg)}
 return response.json();
 }finally{clearTimeout(timeout)} }
function mustList(val,label){if(!Array.isArray(val))throw new Error(`فرمت ${label} معتبر نیست`);return val}
async function refresh({initial=false}={}){if(state.isLoading)return;state.isLoading=true;const button=$('refresh-btn');button.disabled=true;button.textContent='◌ در حال بررسی…';const request=++state.latestRequest;
 try{const [runs,prs,issues]=await Promise.all([
 api('/actions/runs?per_page=25'),api('/pulls?state=open&per_page=50'),api('/issues?state=open&per_page=50')
 ]);
 if(request!==state.latestRequest)return;
 const r=mustList(runs.workflow_runs,'Workflow');const p=mustList(prs,'Pull Requests');const i=mustList(issues,'Issues');
 if(r.length===25||p.length===50||i.length===50)throw new Error('فهرست به سقف یک صفحه رسیده؛ شمارش کامل قابل تأیید نیست');
 state.runs=r;state.prs=p;state.issues=i.filter(x=>!x.pull_request);state.source='live';state.lastVerified=new Date().toISOString();state.error=null;
 render();if(state.selectedRun && state.runs.some(x=>x.id===state.selectedRun))void selectRun(state.selectedRun,{noRender:true});
 }catch(err){state.error=(err&&err.message)||'خطای دریافت داده';if(!initial){$('truth-text').textContent=`اتصال با خطا مواجه شد: ${state.error}. داده‌ها تازه نیستند و نباید برای تصمیم‌گیری به‌عنوان وضعیت فعلی استفاده شوند.`;state.source='snapshot';state.runs=SNAPSHOT.runs;state.prs=SNAPSHOT.prs;state.issues=SNAPSHOT.issues;state.selectedRun=null;state.jobs=[];render();}else{render()}}
 finally{state.isLoading=false;button.disabled=false;button.innerHTML='<span>⟳</span> دریافت آخرین وضعیت';}}
async function selectRun(id,{noRender=false}={}){if(!validId(id))return;state.selectedRun=id;const run=state.runs.find(r=>r.id===id);if(!run)return;
 if(!noRender)renderRuns();$('inspector-subtitle').textContent=run.name||'گزارش اجرا';$('inspector-link').href=runUrl(id);$('inspector-context').textContent=`GitHub Actions #${id}`;
 const isHistorical=state.source!=='live';
 $('inspector').innerHTML=`<div class="inspector-title">${escapeHtml(run.name||'Workflow')}</div><div class="inspector-details">run #${escapeHtml(id)} · ${escapeHtml(jobStatus(run))} · ${escapeHtml(hash(run.head_sha))} · ${escapeHtml(formatDate(run.created_at))}</div><div class="empty-state">${isHistorical?'گزارش مرحله‌های این اجرای تاریخی بدون اتصال شبکه قابل واکشی نیست.':'در حال واکشی مراحل و تست‌های واقعی…'}</div>`;
 if(isHistorical)return;
 const current=++state.jobRequest;
 try{const result=await api(`/actions/runs/${id}/jobs?per_page=100`);if(current!==state.jobRequest||state.selectedRun!==id)return;
 if(!Array.isArray(result.jobs))throw new Error('فهرست Job معتبر نیست');if(result.jobs.length>=100)throw new Error('Jobهای این اجرا بیش از یک صفحه است');state.jobs=result.jobs;state.loadedJobsFor=id;
 const rendered=state.jobs.map(job=>{const stages=Array.isArray(job.steps)?job.steps:[];
 return `<div class="inspector-title" style="margin-top:14px">${escapeHtml(job.name||'Job')} <span class="run-state ${jobStatus(job)}">${stateLabel(jobStatus(job))}</span></div>${stages.map(step=>{const s=jobStatus(step);return `<div class="step"><span class="step-symbol ${s}">${statusSymbol(s)}</span><div class="step-details"><div class="step-name">${escapeHtml(step.name||'مرحله بدون نام')}</div><div class="step-info">${escapeHtml(s)} · ${escapeHtml(formatDate(step.started_at))}</div></div></div>`}).join('')||'<div class="muted">برای این Job اطلاعات قدم‌ها گزارش نشده است.</div>'}`;
 }).join('');
 $('inspector').innerHTML=`<div class="inspector-title">${escapeHtml(run.name||'Workflow')}</div><div class="inspector-details">run #${escapeHtml(id)} · ${escapeHtml(jobStatus(run))} · ${escapeHtml(hash(run.head_sha))} · ${escapeHtml(formatDate(run.created_at))}</div>${rendered||'<div class="empty-state">هنوز اطلاعات Job در GitHub منتشر نشده است.</div>'}`;
 }catch(err){if(state.selectedRun===id)$('inspector').innerHTML=`<div class="error-text">اطلاعات مرحله‌ها دریافت نشد: ${escapeHtml(err.message||'خطای اتصال')}</div><a href="${runUrl(id)}" target="_blank" rel="noopener noreferrer">دیدن مراحل در GitHub ↗</a>`}
}
async function selectPR(id){if(!validId(id))return;state.selectedPR=id;const panel=$('file-panel');panel.innerHTML=`<div class="file-loading">در حال بررسی فایل‌های PR #${id}…</div>`;
 if(state.source!=='live'){panel.innerHTML=`<div class="muted">در حالت داده تاریخی، نام فایل‌ها بارگیری نمی‌شوند. <a href="${prUrl(id)}/files" target="_blank" rel="noopener noreferrer">مشاهده تغییرات در GitHub ↗</a></div>`;return;}
 const current=++state.filesRequest;
 try{const files=mustList(await api(`/pulls/${id}/files?per_page=100`),'Files');if(current!==state.filesRequest||state.selectedPR!==id)return;if(files.length>=100)throw new Error('فهرست فایل‌ها بیش از یک صفحه است');
 panel.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><strong>فایل‌های تغییریافته در PR #${id}</strong><a href="${prUrl(id)}/files" target="_blank" rel="noopener noreferrer">دیدن کد و Diff ↗</a></div>${files.slice(0,20).map(f=>`<div class="file-entry"><span class="file-status ${escapeHtml(f.status==='added'?'added':f.status==='removed'?'removed':'')}">${escapeHtml(f.status||'modified')}</span><span>${escapeHtml(f.filename||'نامشخص')}</span><span class="muted">+${Number(f.additions)||0}/-${Number(f.deletions)||0}</span></div>`).join('')}${files.length>20?`<div>و ${files.length-20} فایل دیگر در GitHub…</div>`:''}`;
 }catch(err){panel.innerHTML=`<div class="error-text">دریافت فایل‌ها ناموفق بود: ${escapeHtml(err.message||'خطای نامعلوم')}</div><a href="${prUrl(id)}/files" target="_blank" rel="noopener noreferrer">باز کردن PR در GitHub ↗</a>`;}
}
function bind(){ $('refresh-btn').addEventListener('click',()=>refresh());$('run-tabs').querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{state.currentFilter=btn.dataset.filter;$('run-tabs').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b===btn));renderRuns()}));
 document.querySelectorAll('.nav-link').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('.nav-link').forEach(x=>x.classList.toggle('active',a===x))}));}
function start(){clock();setInterval(clock,30000);renderAgents();render();bind();void refresh({initial:true});setInterval(()=>{if(document.visibilityState==='visible')void refresh()},REFRESH_MS)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

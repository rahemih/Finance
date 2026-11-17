'use strict';
// Local import of NEXUS QUANT agent trace; no account credentials or actions.
// An intact hash chain is not an authenticated identity or proof of execution.
(() => {
 const REQUIRED = ['agent_id','at_utc','event_hash','event_type','financial_mode','message','prev_hash','run_id','schema_version','seq','target','task_id'];
 const TYPES = new Set(['TASK_STARTED','AGENT_STARTED','HEARTBEAT','TOOL_STARTED','TOOL_FINISHED','FILE_CHANGED','TEST_STARTED','TEST_PASSED','TEST_FAILED','BUG_DETECTED','BUG_FIX_STARTED','BUG_FIXED','HANDOFF','VETO','BLOCKED','AGENT_FINISHED','TASK_FINISHED','ERROR']);
 const bad = new Set(['TEST_FAILED','BUG_DETECTED','VETO','BLOCKED','ERROR']);
 const esc = s => String(s ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const $t=id=>document.getElementById(id);
 const state = {events:[],valid:false,loadedAt:null,filter:'all'};
 const canonical=o=>JSON.stringify(Object.keys(o).sort().reduce((a,k)=>(a[k]=o[k],a),{}));
 const hex = bytes=>Array.from(new Uint8Array(bytes)).map(x=>x.toString(16).padStart(2,'0')).join('');
 async function sha256(value){
  if (!globalThis.crypto?.subtle) throw new Error('مرورگر فاقد Web Crypto امن است؛ نمی‌توان یکپارچگی رویدادها را تأیید کرد.');
  return hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
 }
 async function validate(report){
  if(!report || report.schema_version!=='fin.agent.event.v1' || report.financial_mode!=='DEMO_ONLY' || report.source!=='LOCAL_AGENT_EVENT_JOURNAL' || !Array.isArray(report.events))throw new Error('ساختار یا حالت مالی گزارش معتبر نیست.');
  if(report.events.length>5000)throw new Error('بیش از ۵۰۰۰ رویداد؛ گزارش باید به فایل‌های کوچک‌تر تقسیم شود.');
  let prev='0'.repeat(64);
  for(let i=0;i<report.events.length;i++){
   const item=report.events[i];
   if(!item||typeof item!=='object'||Array.isArray(item)||JSON.stringify(Object.keys(item).sort())!==JSON.stringify(REQUIRED))throw new Error(`خطای ساختار رویداد ${i+1}`);
   if(item.seq!==i+1||item.prev_hash!==prev||!/^A(?:[0-9]|10)$/.test(item.agent_id)||!/^FIN-P\d\d-W[A-Z]-\d{3}(?:-R\d\d)?$/.test(item.task_id)||!TYPES.has(item.event_type)||item.schema_version!=='fin.agent.event.v1'||item.financial_mode!=='DEMO_ONLY')throw new Error(`اطلاعات رویداد ${i+1} معتبر نیست.`);
   if(typeof item.message!=='string'||item.message.length>180||typeof item.target!=='string'||item.target.length>240||typeof item.run_id!=='string'||!Number.isFinite(Date.parse(item.at_utc)))throw new Error(`فیلدهای رویداد ${i+1} نامعتبر است.`);
   const {event_hash,...withoutHash}=item;
   const digest=await sha256(canonical(withoutHash));
   if(event_hash!==digest)throw new Error(`تغییر غیرمجاز رویداد ${i+1} شناسایی شد.`);
   prev=digest;
  }
  if(report.last_hash !== (report.events.length?prev:null))throw new Error('هش نهایی زنجیره معتبر نیست.');
  return report.events;
 }
 const labels={TASK_STARTED:'آغاز کار',AGENT_STARTED:'آغاز ایجنت',HEARTBEAT:'سیگنال فعالیت',TOOL_STARTED:'شروع ابزار',TOOL_FINISHED:'پایان ابزار',FILE_CHANGED:'تغییر فایل',TEST_STARTED:'شروع تست',TEST_PASSED:'تست موفق',TEST_FAILED:'تست ناموفق',BUG_DETECTED:'شناسایی باگ',BUG_FIX_STARTED:'شروع رفع باگ',BUG_FIXED:'رفع باگ ثبت شد',HANDOFF:'انتقال وظیفه',VETO:'وتو',BLOCKED:'مسدود',AGENT_FINISHED:'پایان ایجنت',TASK_FINISHED:'پایان کار',ERROR:'خطا'};
 function render(){
  const status=$t('trace-status'),list=$t('trace-list'),count=$t('trace-count');
  if(!status||!list||!count)return;
  count.textContent=String(state.events.length);
  if(!state.valid){status.textContent='هیچ جریان رویداد امضاشده با هویت مستقل متصل نیست؛ فایل محلی قابل واردکردن است.';list.innerHTML='<div class="empty-state">هنوز گزارش رویداد ایجنتی وارد نشده است. فعالیت GitHub بالا مستقل نمایش داده می‌شود.</div>';return;}
  const last=state.events.at(-1);
  status.textContent=`زنجیره هش بررسی شد · ${state.events.length} رویداد · آخرین زمان ثبت ${last?.at_utc||'—'} · هویت فرستنده احراز نشده · حالت Demo`;
  const items=state.events.filter(x=>state.filter==='all'||x.agent_id===state.filter).slice(-80).reverse();
  list.innerHTML=items.length?items.map(e=>`<div class="trace-event ${bad.has(e.event_type)?'alert':''}"><div class="trace-emblem">${esc(e.agent_id)}</div><div class="trace-event-body"><strong>${esc(labels[e.event_type]||e.event_type)}</strong><span>${esc(e.message)}</span><div class="trace-meta"><code dir="ltr">${esc(e.task_id)}</code><code dir="ltr">${esc(e.target)}</code><time dir="ltr">${esc(e.at_utc)}</time></div></div></div>`).join(''):'<div class="empty-state">برای این ایجنت رویدادی وجود ندارد.</div>';
 }
 function lastForAgent(agent){
  if(!state.valid)return null;
  const last=[...state.events].reverse().find(x=>x.agent_id===agent);
  if(!last)return null;
  const age=Date.now()-Date.parse(last.at_utc);
  const recent=age>=0 && age<120000;
  return {label: (recent?'آخرین گزارش تازه: ':'آخرین گزارش ثبت‌شده: ')+(labels[last.event_type]||last.event_type),level:bad.has(last.event_type)?'failure':'unknown',unverified:true};
 }
 async function importFile(file){
  if(!file||file.size>2_000_000)throw new Error('حجم فایل باید حداکثر ۲ مگابایت باشد.');
  const report=JSON.parse(await file.text());
  const events=await validate(report);
  state.events=events;state.valid=true;state.loadedAt=new Date().toISOString();
  render();if(typeof renderAgents==='function')renderAgents();
 }
 function bind(){
  const picker=$t('trace-file'),select=$t('trace-filter');
  if(!picker||!select)return;
  picker.addEventListener('change',async()=>{
   if(!picker.files?.[0])return;
   try{await importFile(picker.files[0]);$t('trace-error').textContent='';}
   catch(e){state.events=[];state.valid=false;render();if(typeof renderAgents==='function')renderAgents();$t('trace-error').textContent='گزارش رد شد: '+String(e.message||'خطای اعتبارسنجی');}
   finally{picker.value='';}
  });
  select.addEventListener('change',()=>{state.filter=select.value;render();});
  render();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
 window.nexusAgentTrace={lastForAgent,validate,render};
})();

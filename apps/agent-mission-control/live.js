'use strict';
// One-way, same-origin, read-only agent and GitHub event stream; no client keys.
(() => {
 let stream=null;
 const $=id=>document.getElementById(id);
 const gate=$('auth-gate');
 function status(s){if($('trace-status'))$('trace-status').textContent=s}
 async function apply(value){
  if(!value||value.schema_version!=='nq.mission.v3')throw new Error('Invalid API snapshot');
  const gh=value.github;
  if(gh&&Array.isArray(gh.runs)&&Array.isArray(gh.prs)&&Array.isArray(gh.issues)){
   state.runs=gh.runs;state.prs=gh.prs;state.issues=gh.issues;
   state.source=gh.status==='LIVE'?'live':'waiting';
   state.lastVerified=gh.verified_at;state.error=gh.error||null;render();
  }
  if(value.trace&&window.nexusAgentTrace){
   try{
    await window.nexusAgentTrace.loadServer(value.trace);
    if($('runtime-status-text'))$('runtime-status-text').textContent=value.trace.events.length?
      'رویدادهای واقعی ثبت شده‌اند':'متصل؛ منتظر رویداد Runner';
    if($('runtime-led'))$('runtime-led').className='source-led '+(value.trace.events.length?'good':'amber');
   }catch(e){status('گزارش دریافت‌شده نامعتبر است: '+String(e.message||e))}
  }
 }
 window.nexusApplySnapshot=apply;
 async function resync(){
  const r=await fetch('/api/state',{cache:'no-store'});
  if(r.status===401){if(gate)gate.hidden=false;return}
  if(!r.ok)throw new Error('API '+r.status);
  await apply(await r.json());
 }
 function live(){
  if(!('EventSource' in window)){status('مرورگر شما از اتصال زنده SSE پشتیبانی نمی‌کند');return}
  if(stream)stream.close();
  stream=new EventSource('/api/stream');
  stream.addEventListener('open',()=>status('جریان SSE به API متصل است؛ به‌روزرسانی خودکار فعال شد.'));
  stream.addEventListener('snapshot',event=>{try{void apply(JSON.parse(event.data))}catch{status('داده SSE نامعتبر است')}});
  stream.addEventListener('github',event=>{try{
   const gh=JSON.parse(event.data);
   if(!gh||!Array.isArray(gh.runs)||!Array.isArray(gh.prs)||!Array.isArray(gh.issues))return;
   state.runs=gh.runs;state.prs=gh.prs;state.issues=gh.issues;
   state.source=gh.status==='LIVE'?'live':'waiting';state.error=gh.error||null;
   state.lastVerified=gh.verified_at;render();
  }catch{state.source='waiting';renderSource()}});
  stream.addEventListener('trace',()=>{void resync().catch(()=>status('در حال بازیابی شواهد پس از دریافت رویداد'))});
  stream.addEventListener('resync',()=>{void resync().catch(()=>status('جریان رویداد نیازمند همگام‌سازی مجدد است'))});
  stream.onerror=()=>{
   state.source='waiting';state.error='SSE connection lost';renderSource();
   status('ارتباط قطع شد؛ مرورگر بدون Refresh برای اتصال مجدد تلاش می‌کند.');
  };
 }
 async function probe(){
  try{
   const r=await fetch('/api/state',{cache:'no-store'});
   if(r.status===401){if(gate)gate.hidden=false;return}
   if(!r.ok)throw new Error('API '+r.status);
   if(gate)gate.hidden=true;
   await apply(await r.json());
   live();
  }catch{status('API در دسترس نیست؛ اتصال به‌طور خودکار مجدداً بررسی می‌شود.');setTimeout(probe,6500)}
 }
 function bindLogin(){
  const form=$('auth-form');if(!form)return;
  form.addEventListener('submit',async e=>{
   e.preventDefault();
   const pass=$('viewer-password').value;const error=$('auth-error');
   try{
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
                                     body:JSON.stringify({password:pass}),cache:'no-store'});
    if(!r.ok)throw new Error('رمز اشتباه است یا محدودیت تلاش برقرار شده');
    $('viewer-password').value='';
    if(gate)gate.hidden=true;
    live();
   }catch(err){if(error)error.textContent=String(err.message||err)}
  });
 }
 const start=()=>{bindLogin();void probe()};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
'use strict';
/* Mission Control bounded Start/resume audit. Never claims an LLM coding runner is active. */
(() => {
  const $=id=>document.getElementById(id);
  const phases={
    IDLE:'آماده شروع',
    RUNNING:'در حال بررسی واقعی',
    RETRYING:'تلاش مجدد پس از خطای سرویس',
    AUDIT_COMPLETE:'بررسی پایان یافت',
    BLOCKED:'متوقف در مانع معتبر'
  };
  let inFlight=false;
  let lastStatus='IDLE';
  const allowUrl=value=>typeof value==='string'&&/^https:\/\/github\.com\/rahemih\/Finance(?:\/|$)/.test(value);
  function show(control){
    if(!control||control.mode!=='READ_ONLY_RESUME_AUDIT')return;
    const status=control.status||'IDLE', busy=['RUNNING','RETRYING'].includes(status);
    lastStatus=status;
    $('control-status').textContent=phases[status]||'نامعلوم';
    $('control-status').dataset.level=busy?'running':status==='BLOCKED'?'blocked':status==='AUDIT_COMPLETE'?'complete':'idle';
    $('control-run').textContent=control.run_id||'—';
    $('control-phase').textContent=status==='AUDIT_COMPLETE'?'شناسایی کار بعدی':status==='BLOCKED'?'نیازمند رفع مانع':'جمع‌آوری شواهد';
    $('control-attempt').textContent=control.attempt?String(control.attempt)+' / '+String(control.max_attempts||3):'—';
    $('control-main').textContent=typeof control.main_sha==='string'?control.main_sha.slice(0,12):'—';
    const next=control.next_task;
    $('control-next').hidden=!next;
    if(next&&allowUrl(next.url)){
      $('control-next-link').href=next.url;
      $('control-next-link').textContent=(next.kind==='pr'?'PR #':'Issue #')+(next.number??'—')+' · '+String(next.title||'').slice(0,140);
    } else if(next) {
      $('control-next-link').href='https://github.com/rahemih/Finance';
      $('control-next-link').textContent='مشاهده مخزن Finance';
    }
    let message='با Start، یک بررسی واقعی فقط‌خواندنی آغاز می‌شود؛ توسعه خودکار کد نیازمند اتصال Runner است.';
    if(status==='RUNNING')message='در حال بررسی آخرین main، PRها، Issueها و شواهد CI — گزارش مراحل در دفتر رویدادها نمایش داده می‌شود.';
    if(status==='RETRYING')message='یک خطای موقت رخ داده است. سرویس با سقف سه تلاش، بدون ایجاد تغییر در مخزن، دوباره بررسی می‌کند.';
    if(status==='AUDIT_COMPLETE')message='نقطه ادامه و موانع شناسایی شدند. این اجرای بررسی، کدنویسی یا رفع باگ مستقل انجام نمی‌دهد.';
    if(status==='BLOCKED')message='بررسی با مانع واقعی متوقف شد: '+String(control.error||'شواهد کافی نیست').slice(0,170);
    if(control.blockers?.length&&status==='AUDIT_COMPLETE')message+=' موانع باز: '+control.blockers.join('، ').slice(0,300);
    $('control-message').textContent=message;
    const btn=$('control-start');
    btn.disabled=busy||inFlight;
    btn.setAttribute('aria-busy',String(busy||inFlight));
    btn.textContent=busy?'در حال بررسی…':'▶ شروع بررسی و ادامه پروژه';
  }
  window.nexusControlApply=show;
  async function send(){
    if(inFlight)return;
    inFlight=true;
    const button=$('control-start');button.disabled=true;button.textContent='در حال شروع…';
    try{
      const response=await fetch('/api/start',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({action:'resume_audit'}),cache:'no-store'
      });
      const result=await response.json();
      show(result);
      if(response.status===429){
        $('control-message').textContent='برای جلوگیری از درخواست‌های تکراری، بررسی تازه پس از '+(result.retry_after_seconds||'چند')+' ثانیه مجاز است؛ نتایج آخرین اجرا در همین صفحه باقی می‌مانند.';
      }else if(!response.ok){
        $('control-message').textContent='شروع بررسی رد شد: '+String(result.error||'خطای API');
      }
    }catch{
      $('control-message').textContent='API اجرای بررسی فعلاً در دسترس نیست؛ پس از اتصال دوباره تلاش کنید.';
    }finally{
      inFlight=false;
      try{const r=await fetch('/api/control',{cache:'no-store'});if(r.ok)show(await r.json())}catch{}
      button.disabled=['RUNNING','RETRYING'].includes(lastStatus);
    }
  }
  function init(){
    const button=$('control-start');if(!button)return;
    button.addEventListener('click',()=>{void send()});
    void fetch('/api/control',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(show).catch(()=>{});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();

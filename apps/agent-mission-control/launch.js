'use strict';
/* Owner-protected dispatch: never store the token and never claim model work began on HTTP 202. */
(() => {
  const el=id=>document.getElementById(id);
  let configured=false, busy=false;
  function show(state){
    if(!state||state.mode!=='OWNER_AUTHENTICATED_GITHUB_DISPATCH')return;
    configured=!!state.configured;
    const status=state.status||'IDLE';
    const label={
      IDLE:'آماده راه‌اندازی محافظت‌شده',
      BLOCKED_CONFIGURATION:'پیش‌نیازهای سرور تکمیل نشده‌اند',
      REQUESTING_GITHUB:'در حال ارسال درخواست به GitHub',
      DISPATCH_ACCEPTED:'GitHub درخواست را پذیرفت؛ اجرای مدل هنوز تأیید نشده',
      BLOCKED_GITHUB_DISPATCH:'GitHub درخواست را رد کرده یا تأیید نکرد',
      BLOCKED_UNVERIFIED_DISPATCH:'پاسخ اجرای GitHub قابل تأیید نیست'
    }[status]||status;
    el('operator-status').textContent=label;
    if(!configured){
      el('operator-message').textContent='برای آغاز کدنویسی واقعی، توکن اختصاصی مالک و توکن محدود GitHub Actions در تنظیمات خصوصی Render لازم‌اند؛ کلید OpenAI هم باید در GitHub Actions ثبت شده باشد.';
    }else if(status==='DISPATCH_ACCEPTED'){
      el('operator-message').textContent='درخواست اجرای وظیفه FIN-P24-WZ-008 به GitHub ارسال و پذیرفته شد. برای تأیید کدنویسی و تست‌ها، اجرای جدید را در GitHub Actions مشاهده کنید؛ موفقیت هنوز قطعی نیست.';
    }else if(status.startsWith('BLOCKED_')&&status!=='BLOCKED_CONFIGURATION'){
      el('operator-message').textContent='اجرای واقعی هنوز شروع نشده: '+(state.error||label);
    }else{
      el('operator-message').textContent='مجاز به اجرای فقط یک وظیفه محدود، با بررسی مستقل تست‌ها و PR پیشنهادی. وضعیت واقعی بعد از پاسخ GitHub مشخص می‌شود.';
    }
    el('operator-launch').disabled=!configured||busy;
  }
  window.nexusLaunchApply=show;
  async function begin(){
    if(!configured||busy)return;
    const key=el('owner-start-token').value;
    if(key.length<32){
      el('operator-message').textContent='توکن مالک معتبر نیست. این کلید را فقط از تنظیمات خصوصی خود دریافت کنید؛ آن را اینجا در گفتگو نفرستید.';
      return;
    }
    busy=true;
    el('operator-launch').disabled=true;
    el('operator-message').textContent='در حال درخواست اجرای ثابت در GitHub Actions…';
    try{
      const res=await fetch('/api/launch',{
        method:'POST',cache:'no-store',
        headers:{'Authorization':'Bearer '+key,'Content-Type':'application/json'},
        body:JSON.stringify({action:'run_fixed_governed_task'})
      });
      const response=await res.json();
      if(res.status===202){
        el('operator-message').textContent='GitHub درخواست را پذیرفت؛ هنوز تولید کد، اجرای تست‌ها یا ساخت PR تأیید نشده است. نتیجه را در GitHub Actions ببینید.';
        void fetch('/api/launcher',{cache:'no-store'}).then(r=>r.json()).then(show).catch(()=>{});
      }else if(res.status===401){
        el('operator-message').textContent='توکن مالک نادرست است؛ هیچ عملیات تغییردهنده‌ای اجرا نشد.';
      }else if(res.status===429){
        el('operator-message').textContent='برای جلوگیری از چندبار اجرا شدن، تلاش بعدی پس از '+(response.retry_after_seconds||'مدتی')+' ثانیه مجاز است.';
      }else{
        el('operator-message').textContent='اجرای GitHub تأیید نشد: '+String(response.status||response.error||'UNKNOWN');
      }
    }catch{
      el('operator-message').textContent='اتصال به API راه‌اندازی ناموفق بود. در وضعیت نامطمئن، برای جلوگیری از اجرای تکراری خودکار دوباره درخواست ارسال نمی‌شود.';
    }finally{
      el('owner-start-token').value='';
      busy=false;
      el('operator-launch').disabled=!configured;
    }
  }
  function init(){
    const btn=el('operator-launch');if(!btn)return;
    btn.addEventListener('click',()=>{void begin()});
    void fetch('/api/launcher',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(show).catch(()=>{
      el('operator-message').textContent='وضعیت اتصال راه‌انداز GitHub در دسترس نیست.';
      btn.disabled=true;
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();

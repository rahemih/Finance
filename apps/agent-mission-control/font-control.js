'use strict';
/*
 * NEXUS QUANT private browser font loader.
 * A user-picked font is kept only in this browser's IndexedDB, never uploaded
 * to GitHub, Render, an API endpoint or a backend log.
 */
(() => {
 const DB_NAME='nq-mission-control-personal-font-v1';
 const STORE='user-font';
 const KEY='iranian-sans';
 const FAMILY='NQ User Iranian Sans';
 const MAX_BYTES=1024*1024;
 let active=null;
 const $=id=>document.getElementById(id);
 const say=message=>{const el=$('font-status');if(el)el.textContent=message};
 function openDB(){
  return new Promise((resolve,reject)=>{
   if(!('indexedDB' in window))return reject(new Error('IndexedDB unavailable'));
   const request=indexedDB.open(DB_NAME,1);
   request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(STORE))db.createObjectStore(STORE)};
   request.onsuccess=()=>resolve(request.result);
   request.onerror=()=>reject(request.error||new Error('Font storage failed'));
  });
 }
 async function saved(){
  const db=await openDB();
  try{return await new Promise((resolve,reject)=>{
   const tx=db.transaction(STORE,'readonly'),req=tx.objectStore(STORE).get(KEY);
   req.onsuccess=()=>resolve(req.result||null);
   req.onerror=()=>reject(req.error||new Error('Stored font unavailable'));
  })}finally{db.close()}
 }
 async function persist(bytes){
  const db=await openDB();
  try{return await new Promise((resolve,reject)=>{
   const tx=db.transaction(STORE,'readwrite');
   tx.objectStore(STORE).put(bytes,KEY);
   tx.oncomplete=()=>resolve();
   tx.onerror=()=>reject(tx.error||new Error('Font save failed'));
   tx.onabort=()=>reject(tx.error||new Error('Font save cancelled'));
  })}finally{db.close()}
 }
 async function activate(bytes){
  if(!(bytes instanceof ArrayBuffer)||!bytes.byteLength||bytes.byteLength>MAX_BYTES)throw Error('Invalid font file size');
  const face=new FontFace(FAMILY,bytes,{style:'normal',weight:'100 900'});
  await face.load();
  if(active)document.fonts.delete(active);
  document.fonts.add(face);
  active=face;
  document.documentElement.style.setProperty('--nq-personal-font',JSON.stringify(FAMILY));
 }
 async function choose(file){
  if(!file)return;
  if(file.size<=0||file.size>MAX_BYTES||!/\.(ttf|otf|woff2?)$/i.test(file.name||'')){
   say('فایل فونت معتبر نیست؛ فقط TTF، OTF یا WOFF تا ۱ مگابایت.');
   return;
  }
  try{
   say('در حال بارگذاری فونت روی همین دستگاه…');
   const bytes=await file.arrayBuffer();
   await activate(bytes);
   try{await persist(bytes);say('فونت ایرانی شما ذخیره شد؛ دفعات بعد خودکار استفاده می‌شود.')}
   catch{say('فونت برای همین نشست فعال است؛ مرورگر اجازه ذخیره دائم نداد.')}
  }catch{say('بارگذاری فونت ناموفق بود؛ فایل ارسالی را دوباره انتخاب کنید.')}
 }
 async function start(){
  const button=$('font-upload-button'),input=$('font-upload-input');
  if(!button||!input)return;
  button.addEventListener('click',()=>input.click());
  input.addEventListener('change',()=>{void choose(input.files?.[0]);input.value=''});
  try{
   const bytes=await saved();
   if(bytes){await activate(bytes);say('فونت Iranian Sans ذخیره‌شده فعال است.')}
   else say('برای استفاده از فونت ارسالی، یک بار «انتخاب فونت» را بزنید.');
  }catch{say('می‌توانید فونت Iranian Sans را برای این مرورگر انتخاب کنید.')}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else void start();
})();

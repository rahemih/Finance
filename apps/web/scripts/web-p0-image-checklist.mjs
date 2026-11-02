import {readFileSync,writeFileSync} from "node:fs";
import {join} from "node:path";

function renderChecklist(baseline,ledger){
 const requireOk=(condition,why)=>{if(!condition)throw new Error("INVALID_CHECKLIST_EVIDENCE: "+why);};
 const check=x=>x?"[x]":"[ ]";
 requireOk(baseline.scope==="WEB-P0-34-PAGES-212-REFERENCES","unexpected source scope");
 requireOk(baseline.pageCount===baseline.pages.length,"page count mismatch");
 const refs=baseline.pages.flatMap(p=>p.images.map(i=>({page:p.pageId,...i})));
 requireOk(refs.length===baseline.referenceCount,"reference count mismatch");
 const refIds=new Set(refs.map(x=>x.screenshotId));
 requireOk(refIds.size===refs.length,"duplicate design screenshot IDs");
 const items=ledger.renderedScreenshots||[],ids=new Set();
 for(const x of items){
  requireOk(!ids.has(x.id),"duplicate output id "+x.id);ids.add(x.id);
  requireOk(baseline.pages.some(p=>p.pageId===x.pageId),"unknown page "+x.id);
  requireOk(/^([0-9a-f]{64})$/.test(x.sha256),"missing verified sha for "+x.id);
  requireOk(x.dimensions.width>0&&x.dimensions.height>0,"dimensions invalid "+x.id);
  requireOk(Number.isInteger(x.evidence.actionsRunId)&&Number.isInteger(x.evidence.artifactId),"missing GitHub artifact "+x.id);
  requireOk(x.pngFilename.endsWith(".png"),"missing png filename "+x.id);
  if(x.designScreenshotId){requireOk(refIds.has(x.designScreenshotId),"invalid 1:1 baseline mapping for "+x.id);}
  requireOk(x.evidence.imageBinaryCommittedToGit===false||!!x.evidence.gitBlobPath,"Git PNG claim missing actual blob path "+x.id);
  requireOk(x.evidence.renderedOwnerApproved===false||!!x.evidence.ownerAcceptanceRef,"owner approval cannot be asserted without evidence "+x.id);
 }
 const completeBaseline=refs.filter(i=>i.ownerDesignReferenceApproved===true&&!!i.googleDocInlineObjectId).length;
 const produced=items.filter(i=>i.sha256&&i.dimensions.width&&i.dimensions.height).length;
 const gh=items.filter(i=>i.evidence.artifactId&&i.evidence.actionsRunId).length;
 const displayed=items.filter(i=>i.evidence.shownInConversation===true).length;
 const binary=items.filter(i=>i.evidence.imageBinaryCommittedToGit===true).length;
 const accepted=items.filter(i=>i.evidence.renderedOwnerApproved===true).length;
 const mapped=items.filter(i=>!!i.designScreenshotId).length;
 const out=[];
 out.push("# NEXUS QUANT — چک‌لیست مرکزی تصاویر WEB-P0","");
 out.push("> **مرجع طراحی فقط تصاویر تأییدشده در Google Docs است.** این چک‌لیست بین «تصویر مرجع» و «خروجی واقعی مرورگر» تفاوت می‌گذارد. هر تیک از قراردادها و شواهد ثبت‌شده تولید می‌شود، نه ادعای پیشرفت.","");
 out.push("## گزارش وضعیت","");
 out.push(`- تصاویر مرجع Google Docs: **${completeBaseline}/${refs.length} تأییدشده** در **${baseline.pages.length} صفحه**.`);
 out.push(`- خروجی‌های مرورگر دارای فایل PNG و هش معتبر: **${produced}** (تعداد خروجی‌ها، نه تعداد تصاویر مرجع تکمیل‌شده).`);
 out.push(`- خروجی‌های ثبت‌شده به‌صورت GitHub Actions Artifact: **${gh}**.`);
 out.push(`- خروجی‌هایی که نمایش در همین گفتگو برایشان ثبت شده: **${displayed}**.`);
 out.push(`- PNGهای دارای Git blob ثبت و تأییدشده: **${binary}**.`);
 out.push(`- خروجی‌های دارای تأیید نهایی مستقل مالک: **${accepted}**.`);
 out.push(`- نگاشت یک‌به‌یک اثبات‌شده از خروجی مرورگر به شناسه تصویر مرجع: **${mapped}/${refs.length}**.`);
 out.push("","### راهنمای تیک‌ها","");
 out.push("- `[x]` یعنی شواهد همان ستون موجود است؛ `[ ]` یعنی انجام‌شدن آن تأیید نشده است. خالی‌بودن ستون به معنی شکست فنی نیست.");
 out.push("- ستون «Google Docs» تنها **تأیید طرح مرجع** است؛ به‌هیچ‌وجه معادل تأیید خروجی کدنویسی‌شده نیست.");
 out.push("- «ثبت در GitHub Actions» با «وجود فایل PNG در Git» یکسان نیست. Artifact ممکن است بر اساس Retention منقضی شود.");
 out.push("- تنها زمانی برای یک تصویر مرجع، ستون ساخت/ثبت تیک می‌خورد که خروجی **با همان `screenshotId`** و شواهد معتبر یک‌به‌یک ثبت شود.");
 out.push("- تمام خروجی‌های فعلی غیرعملیاتی هستند. وضعیت CI/Governance و Human Gate مستقل است.","");
 out.push("## جدول صفحه‌ها","");
 out.push("| صفحه | تصاویر مرجع | تأیید Google Docs | خروجی Chromium ثبت‌شده (نگاشت‌نشده) | تکمیل دقیق تصویر مرجع |");
 out.push("|---|---:|---:|---:|---:|");
 for(const p of [...baseline.pages].sort((a,b)=>Number(a.pageId)-Number(b.pageId))){
  const c=items.filter(i=>i.pageId===p.pageId).length;
  const m=items.filter(i=>i.pageId===p.pageId&&i.designScreenshotId).length;
  const ok=p.images.filter(i=>i.ownerDesignReferenceApproved&&i.googleDocInlineObjectId).length;
  out.push(`| ${p.pageId} | ${p.images.length} | ${ok} | ${c} | ${m} |`);
 }
 out.push("","## چک‌لیست تک‌تک تصاویر مرجع (۲۱۲ مورد)","");
 out.push("برای هر شناسه، تأیید اصل تصویر در سند تیک خورده است؛ **ساخت و ثبتِ نسخه کدنویسی‌شده با همان شناسه** تا اثبات تطبیق، تیک نمی‌خورد.","");
 for(const p of [...baseline.pages].sort((a,b)=>Number(a.pageId)-Number(b.pageId))){
  out.push(`### صفحه ${p.pageId} — ${p.images.length} تصویر`,"");
  out.push("| شناسه تصویر سند | تأیید تصویر مرجع | خروجی همان شناسه ساخته | نمایش در گفتگو | تصویر در GitHub ثبت | تأیید خروجی |");
  out.push("|---|:---:|:---:|:---:|:---:|:---:|");
  for(const ref of p.images){
   const hit=items.find(i=>i.designScreenshotId===ref.screenshotId);
   const produced=!!hit?.sha256;
   const shown=!!hit?.evidence.shownInConversation;
   const git=!!hit?.evidence.artifactId&&!!hit?.evidence.actionsRunId;
   const ok=!!hit?.evidence.renderedOwnerApproved&&!!hit?.evidence.ownerAcceptanceRef;
   out.push(`| \`${ref.screenshotId}\` | ${check(!!ref.ownerDesignReferenceApproved&&!!ref.googleDocInlineObjectId)} | ${check(produced)} | ${check(shown)} | ${check(git)} | ${check(ok)} |`);
  }
  out.push("");
 }
 out.push("## خروجی‌های تصویری واقعی (دارای مدرک مستقل)","");
 out.push("**توجه:** این ۲۱ PNG یک‌به‌یک به ۲۱۲ شناسه تصاویر سند نگاشت نشده‌اند؛ ثبت خروجی مرورگر، اجازه تیک‌زدن تصویر مرجع را نمی‌دهد.","");
 out.push("| شناسه خروجی | صفحه / اندازه | ساخته | در گفتگو نمایش | ثبت Actions | PNG در Git | تأیید نهایی | مدرک GitHub |");
 out.push("|---|---|:---:|:---:|:---:|:---:|:---:|---|");
 for(const x of [...items].sort((a,b)=>Number(a.pageId)-Number(b.pageId)||a.id.localeCompare(b.id))){
  const ev=x.evidence;
  const registered=!!ev.actionsRunId&&!!ev.artifactId;
  out.push(`| \`${x.id}\` | ${x.pageId} · ${x.dimensions.width}×${x.dimensions.height} | ${check(!!x.sha256)} | ${check(ev.shownInConversation===true)} | ${check(registered)} | ${check(ev.imageBinaryCommittedToGit===true)} | ${check(ev.renderedOwnerApproved===true)} | [CI #${ev.actionsRunId}](https://github.com/rahemih/Finance/actions/runs/${ev.actionsRunId}) · [PR #${ev.sourcePr}](https://github.com/rahemih/Finance/pull/${ev.sourcePr}) |`);
 }
 out.push("","## دستور به‌روزرسانی در هر گام","");
 out.push("۱. خروجی واقعی را بساز و **در همین گفتگو** نمایش بده.");
 out.push("۲. فایل PNG و SHA-256 و اندازه را کنترل کن؛ در GitHub ثبت کن و شناسه Run/Artifact یا مسیر Blob معتبر بگیر.");
 out.push("۳. یک رکورد با شناسه خروجی یکتا به `apps/web/contracts/web-p0-image-evidence.json` اضافه کن؛ `shownInConversation` را فقط پس از نمایش واقعی `true` کن.");
 out.push("۴. اگر و فقط اگر نگاشت قطعی با یکی از تصاویر مرجع وجود دارد، فیلد `designScreenshotId` را اضافه کن؛ در غیر این صورت این فیلد را خالی بگذار.");
 out.push("۵. چک‌لیست را با `node apps/web/scripts/web-p0-image-checklist.mjs --write` بازتولید کن. CI با `--check` از قدیمی‌ماندن آن جلوگیری می‌کند.");
 out.push("۶. **تأیید ظاهر خروجی، رفع Governance و مجوز ادغام** جداگانه انجام می‌شوند؛ تیک ساخت/ثبت به معنی تکمیل پروژه نیست.","");
 out.push("## اسناد مبنا","");
 out.push("- [سند اصلی Google Docs](https://docs.google.com/document/d/19trhKWaIB9YUqc3h7sgrovKwRiJKFUM_RSjmj6NDPQ0/edit)");
 out.push("- `apps/web/contracts/visual-reference-approval.json` — ۳۴ صفحه، ۲۱۲ تصویر مرجع تأییدشده.");
 out.push("- `apps/web/contracts/web-p0-image-evidence.json` — شواهد ۲۱ خروجی مرورگر.");
 out.push("- `apps/web/visual-fixtures/page-001-login/registration.json` — ثبت صفحه ورود و SHA-256 های مستقل.");
 out.push("- [PR #512](https://github.com/rahemih/Finance/pull/512) — ثبت صفحه ورود، Draft؛ [PR #509](https://github.com/rahemih/Finance/pull/509) — صفحات بازار، Draft.");
 return out.join("\n")+"\n";
}

const root=process.cwd();
const baseline=JSON.parse(readFileSync(join(root,"apps/web/contracts/visual-reference-approval.json"),"utf8"));
const evidence=JSON.parse(readFileSync(join(root,"apps/web/contracts/web-p0-image-evidence.json"),"utf8"));
const output=join(root,"apps/web/docs/WEB-P0-IMAGE-CHECKLIST.md");
const rendered=renderChecklist(baseline,evidence);
if(process.argv.includes("--check")){
 const saved=readFileSync(output,"utf8");
 if(saved!==rendered){console.error("WEB_P0_IMAGE_CHECKLIST_STALE: run node apps/web/scripts/web-p0-image-checklist.mjs --write");process.exitCode=1;}
 else console.log("WEB_P0_IMAGE_CHECKLIST=PASS refs=212 pages=34 captured="+evidence.renderedScreenshots.length);
} else if(process.argv.includes("--write")){
 writeFileSync(output,rendered,"utf8");
 console.log("WEB_P0_IMAGE_CHECKLIST_WRITTEN="+output);
} else {
 process.stdout.write(rendered);
}

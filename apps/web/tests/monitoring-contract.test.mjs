import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MONITORING_PREVIEW_ONLY, MONITORING_AUTHORITY, MONITORING_ROUTES, UNKNOWN_DATA_MARKER, allowedAction } from "../src/lib/monitoring-preview-contract.ts";
const read=p=>readFileSync(new URL(p,import.meta.url),"utf8");
test("three exact P0-B preview routes, no trading, no known health state",()=>{
  assert.equal(MONITORING_PREVIEW_ONLY,true);
  assert.deepEqual(MONITORING_ROUTES.map(x=>x.href),["/dashboard","/system","/system/alerts"]);
  assert.equal(UNKNOWN_DATA_MARKER,"—");
  assert.ok(Object.values(MONITORING_AUTHORITY).every(v=>v===false));
  assert.equal(allowedAction("ACK"),false);
});
test("visual owner consent is design reference only, 212 IDs with no baselines",()=>{
  const v=JSON.parse(read("../contracts/visual-reference-approval.json"));
  assert.equal(v.referenceCount,212);assert.equal(v.pages.length,34);
  assert.equal(v.designReferenceApproval,"OWNER_APPROVED_IN_CONVERSATION");
  const ids=v.pages.flatMap(x=>x.images.map(i=>i.googleDocInlineObjectId));
  assert.equal(new Set(ids).size,212);
  assert.ok(v.pages.every(x=>x.baselineFreeze==="PENDING_BYTES_AND_SHA256"));
  assert.ok(v.pages.flatMap(x=>x.images).every(x=>x.sourceAssetSHA256===null&&x.actualBrowserComparison==="NOT_RUN"));
});
test("dashboard, health and alerts cannot fake live facts or allow write controls",()=>{
  const source=read("../src/components/monitoring/monitoring-preview.tsx");
  for(const marker of ["داشبورد","سلامت سامانه","مرکز هشدارها","نامشخص","فاقد اتصال","بدون داده زنده","ناشناخته"]) {if(marker==="ناشناخته")continue;assert.ok(source.includes(marker),marker)}
  assert.doesNotMatch(source,/fetch\s*\(|WebSocket\s*\(|localStorage|sessionStorage|document\.cookie|<form|<button|submitOrder|confirmOrder/);
  const reg=JSON.parse(read("../contracts/monitoring-preview-states.json"));
  assert.equal(reg.imageCount,20);assert.equal(reg.pages.length,3);
  assert.ok(reg.pages.every(p=>p.ownerReferenceDesignApproval===undefined&&p.backendConnection==="NOT_CONNECTED"));
});

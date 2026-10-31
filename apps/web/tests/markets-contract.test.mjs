import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
const root="apps/web/";
const contract=JSON.parse(readFileSync(root+"contracts/markets-preview-states.json","utf8"));
test("three canonical P0-C routes are covered",()=>{
 assert.deepEqual(contract.pages.map(x=>x.route),["/markets","/markets/watchlist","/markets/[asset]"]);
 assert.equal(contract.liveTrading,"DISABLED");
 assert.equal(contract.backendConnection,"NOT_CONNECTED");
 assert.equal(contract.ownerRuntimeAcceptance,"PENDING");
});
test("all routes have isolated noindex page entrypoints",()=>{
 const entry=["src/app/markets/page.tsx","src/app/markets/watchlist/page.tsx","src/app/markets/[asset]/page.tsx"];
 for (const f of entry){assert.ok(existsSync(root+f));assert.match(readFileSync(root+f,"utf8"),/index:false,follow:false/)}
});
test("fail closed preview is not an authenticated market feed or order interface",()=>{
 const source=readFileSync(root+"src/components/markets/markets-preview.tsx","utf8");
 for(const term of ["PREVIEW ONLY","بدون داده زنده","LIVE / AUTO غیرفعال","UNKNOWN","disabled","/markets/watchlist"])assert.ok(source.includes(term),term);
 for(const forbidden of [/fetch\s*\(/,/WebSocket\s*\(/,/localStorage/,/placeOrder/,/submitOrder/])assert.doesNotMatch(source,forbidden);
});

test("Next16 server proxy rejects unsafe market page methods before render",()=>{
 const file=root+"src/proxy.ts";
 assert.ok(existsSync(file));
 const source=readFileSync(file,"utf8");
 for(const expected of ['matcher: ["/markets/:path*"]','request.method !== "GET"','request.method !== "HEAD"',"status: 405",'Allow: "GET, HEAD"','"Cache-Control": "no-store"'])assert.ok(source.includes(expected),expected);
});

test("P0-C market, watchlist and detail structures include approved data headings",()=>{
 const c=readFileSync(root+"src/components/markets/markets-preview.tsx","utf8");
 for (const term of ["marketHeaders","watchHeaders","detailTabs","Source: UNCONNECTED","تازگی مظنه","فهرست پیگیری من","تکنیکال","جریان سفارش","نقدشوندگی"])assert.ok(c.includes(term),term);
 assert.match(readFileSync(root+"src/styles/markets-preview.css","utf8"),/max-width:600px/);
});
test("asset detail is fixture only and unknown canonical IDs fail closed",()=>{
 const c=readFileSync(root+"src/app/markets/[asset]/page.tsx","utf8");
 assert.match(c,/asset!==\"mock-btcusdt\"/);
 assert.match(c,/notFound\(\)/);
});

// Anonymous HTTP integration checks; never log cookies or response documents.
const fs = require('fs');
const [base, output] = process.argv.slice(2);
if (!base || !output || !/^https:\/\//.test(base)) throw new Error('Usage: node verify_preview.cjs HTTPS_BASE NEW_REPORT');
if (fs.existsSync(output)) throw new Error('Choose a new evidence file');
const report = {base, checked_at: new Date().toISOString(), scope: 'anonymous-read-only', checks: []};
async function check(method, path, expected, marker) {
 let row = {method, path, expected};
 for(let attempt=1;attempt<=2;attempt++) {
  try {
   const response = await fetch(base + path, {method, signal: AbortSignal.timeout(20000)});
   const html = await response.text();
   row = {...row, status: response.status, cache_control: response.headers.get('cache-control'),
    marker_present: marker ? html.includes(marker) : true, attempt};
   row.passed = row.status === expected && row.marker_present && row.cache_control === 'private, no-store';
   break;
  } catch(error) { row = {...row, passed: false, error: error.name, attempt}; }
 }
 report.checks.push(row);
 console.log(JSON.stringify(row));
 fs.writeFileSync(output, JSON.stringify(report, null, 2));
}
(async()=>{
 const cases = [
  ['GET','/health/live',200,'ok'], ['GET','/health/ready',200,'ready'],
  ['GET','/',200,'共 336 項商品'], ['GET','/product/007b9fa91f1e7f506cb21d54',200,'會員與購物功能尚未開放'],
  ['GET','/?q=SAM_NO_MATCH_20261012',200,'目前沒有符合條件的商品'],
  ['GET','/auth/login',403], ['GET','/admin/',403], ['GET','/cart',403], ['POST','/checkout',403],
 ];
 for(let i=0;i<cases.length;i+=3) await Promise.all(cases.slice(i,i+3).map(args=>check(...args)));
 report.passed = report.checks.every(row=>row.passed);
 fs.writeFileSync(output, JSON.stringify(report, null, 2));
 process.exitCode = report.passed ? 0 : 1;
})().catch(error=>{console.error(error.name);process.exitCode=1;});

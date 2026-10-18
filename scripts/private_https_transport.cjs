// One HTTPS request over stdin/stdout pipes; no listening port or browser proxy.
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
require('node:dns').setDefaultResultOrder('ipv4first');
const traceFile = path.join(os.tmpdir(), 'ren-private-https-' + process.ppid + '.jsonl');
const started = Date.now();
function trace(event, fields = {}) {
  fs.appendFileSync(traceFile, JSON.stringify({ at: new Date().toISOString(),
    event, elapsed_ms: Date.now() - started, ...fields }) + '\n');
}
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', async () => {
  try {
    const request = JSON.parse(input);
    const url = new URL(request.url);
    if (url.protocol !== 'https:' || url.hostname !== 'vibecart-acceptance-pr21-m44ncgz5ta-de.a.run.app'
        || url.username || url.password || url.port) throw Error('scope');
    trace('request', { method: request.method, path: url.pathname });
    const response = await fetch(url, {
      method: request.method, headers: request.headers,
      body: request.body_base64 == null ? undefined : Buffer.from(request.body_base64, 'base64'),
      redirect: 'manual', signal: AbortSignal.timeout(60000),
    });
    trace('headers', { status: response.status });
    const headers = [...response.headers].filter(([name]) => name.toLowerCase() !== 'set-cookie');
    for (const value of response.headers.getSetCookie()) headers.push(['set-cookie', value]);
    const body = Buffer.from(await response.arrayBuffer());
    trace('completed', { status: response.status, bytes: body.length });
    process.stdout.write(JSON.stringify({status: response.status, headers,
      body_base64: body.toString('base64')}),
      () => process.exit(0)); // Finish after flushing; do not retain an idle HTTPS pool.
  } catch (error) {
    trace('failed', { type: error.name, code: error.cause?.code || null });
    process.stdout.write(JSON.stringify({error: 'Private HTTPS request failed', type: error.name,
      code: error.cause?.code || null}), () => process.exit(1));
  }
});

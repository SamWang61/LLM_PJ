// Read-only, redacted Cloud Run log classifier. Raw log messages stay local.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
async function main() {
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  const since = process.argv.find(arg => arg.startsWith('--since='))?.slice('--since='.length);
  const revision = process.argv.find(arg => arg.startsWith('--revision='))?.slice('--revision='.length);
  if (since && Number.isNaN(Date.parse(since))) throw new Error('Invalid --since timestamp');
  if (revision && !/^vibecart-web-[a-z0-9-]+$/.test(revision)) throw new Error('Invalid --revision');
  const after = since || new Date(Date.now() - 25 * 60_000).toISOString();
  const filter = `resource.type="cloud_run_revision" AND resource.labels.service_name="vibecart-web" AND timestamp>="${after}"`
    + (revision ? ` AND resource.labels.revision_name="${revision}"` : '');
  const response = await fetch('https://logging.googleapis.com/v2/entries:list', {
    method: 'POST', signal: AbortSignal.timeout(30000),
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ resourceNames: ['projects/vibecart-llmai'], pageSize: 100,
      orderBy: 'timestamp desc', filter }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(`Logging API HTTP ${response.status} ${body.error?.status || ''}`);
  const entries = body.entries || [];
  const classes = { mongo_selection: 0, mongo_other: 0, app_database_unavailable: 0,
    http_5xx: 0, other_error: 0 };
  const http_statuses = {};
  for (const entry of entries) {
    const raw = JSON.stringify(entry.jsonPayload || entry.textPayload || '');
    const status = entry.httpRequest?.status;
    if (status) http_statuses[status] = (http_statuses[status] || 0) + 1;
    if (/ServerSelectionTimeout|ReplicaSetNoPrimary|connection.*timed?out/i.test(raw)) classes.mongo_selection++;
    else if (/pymongo|MongoDB|MongoClient/i.test(raw)) classes.mongo_other++;
    else if (/database operation unavailable|Database request unavailable/i.test(raw)) classes.app_database_unavailable++;
    else if (/\b5\d\d\b/.test(raw)) classes.http_5xx++;
    else if (['ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY'].includes(entry.severity)) classes.other_error++;
  }
  process.stdout.write(JSON.stringify({ checked_at: new Date().toISOString(), period_start: after, revision: revision || null,
    entries: entries.length, next_page: !!body.nextPageToken, http_statuses, classes }) + '\n');
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

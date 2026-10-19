// Read-only, redacted Cloud Run log classifier. Raw log messages stay local.
const path = require('node:path');
const ERROR_SEVERITIES = new Set(['ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY']);

function summarize(entries) {
  const classes = { mongo_selection: 0, mongo_other: 0, app_database_unavailable: 0,
    http_5xx: 0, other_error: 0 };
  const http_statuses = {};
  for (const entry of entries) {
    const raw = JSON.stringify(entry.jsonPayload || entry.textPayload || '');
    const status = Number(entry.httpRequest?.status);
    if (Number.isInteger(status) && status >= 100 && status <= 599)
      http_statuses[status] = (http_statuses[status] || 0) + 1;
    const httpFailure = status >= 500 && status <= 599;
    if (httpFailure) classes.http_5xx++;
    const databaseUnavailable = /database operation unavailable|Database request unavailable/i.test(raw);
    const selectionFailure = /ServerSelectionTimeout|ReplicaSetNoPrimary|connection.*timed?out/i.test(raw);
    // A successful informational MongoDB log is not an application error.
    const mongoFailure = /pymongo|MongoDB|MongoClient/i.test(raw)
      && (ERROR_SEVERITIES.has(entry.severity) || /exception|traceback|error|failed/i.test(raw));
    if (databaseUnavailable) classes.app_database_unavailable++;
    if (selectionFailure) classes.mongo_selection++;
    else if (mongoFailure) classes.mongo_other++;
    if (ERROR_SEVERITIES.has(entry.severity) && !httpFailure
        && !databaseUnavailable && !selectionFailure && !mongoFailure) classes.other_error++;
  }
  return { http_statuses, classes };
}

async function readLogs(fetchPage, { after, revision, maxPages = 20 }) {
  if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 100)
    throw new Error('Invalid page limit');
  const start = new Date(after);
  if (!Number.isFinite(start.getTime())) throw new Error('Invalid --since timestamp');
  if (revision && !/^vibecart-web-[a-z0-9-]+$/.test(revision)) throw new Error('Invalid --revision');
  const filter = `resource.type="cloud_run_revision" AND resource.labels.service_name="vibecart-web" AND timestamp>="${start.toISOString()}"`
    + (revision ? ` AND resource.labels.revision_name="${revision}"` : '');
  const entries = [], tokens = new Set();
  let pageToken, pages = 0;
  do {
    const body = await fetchPage({ resourceNames: ['projects/vibecart-llmai'], pageSize: 100,
      orderBy: 'timestamp desc', filter, ...(pageToken ? { pageToken } : {}) });
    if (!body || (body.entries !== undefined && !Array.isArray(body.entries)))
      throw new Error('Invalid Logging response');
    entries.push(...(body.entries || []));
    pages++;
    pageToken = body.nextPageToken || undefined;
    if (pageToken && tokens.has(pageToken)) throw new Error('Repeated Logging page token');
    if (pageToken) tokens.add(pageToken);
  } while (pageToken && pages < maxPages);
  const summary = summarize(entries);
  const errors = Object.values(summary.classes).some(value => value > 0);
  return { checked_at: new Date().toISOString(), period_start: start.toISOString(),
    revision: revision || null, entries: entries.length, pages, next_page: !!pageToken,
    complete: !pageToken, status: pageToken ? 'incomplete' : errors ? 'errors_observed'
      : entries.length ? 'no_errors_observed' : 'no_observations', ...summary };
}

async function main() {
  const auth = require(require.resolve('firebase-tools/lib/auth.js', {
    paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
  }));
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  const since = process.argv.find(arg => arg.startsWith('--since='))?.slice('--since='.length);
  const revision = process.argv.find(arg => arg.startsWith('--revision='))?.slice('--revision='.length);
  const after = since || new Date(Date.now() - 25 * 60_000).toISOString();
  const report = await readLogs(async request => {
    const response = await fetch('https://logging.googleapis.com/v2/entries:list', {
      method: 'POST', signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(`Logging API HTTP ${response.status} ${body.error?.status || ''}`);
    return body;
  }, { after, revision });
  process.stdout.write(JSON.stringify(report) + '\n');
  if (!report.complete || report.status !== 'no_errors_observed') process.exitCode = 2;
}

module.exports = { summarize, readLogs };
if (require.main === module) {
  main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
}

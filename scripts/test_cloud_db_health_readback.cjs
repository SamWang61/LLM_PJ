const { test } = require('node:test');
const assert = require('node:assert/strict');
const { summarize, readLogs } = require('./cloud_db_health_readback.cjs');
const options = { after: '2026-10-19T00:50:00Z', revision: 'vibecart-web-n06-294c-1019' };

test('HTTP 503 without payload is counted, even with a database exception', () => {
  const report = summarize([{ httpRequest: { status: 503 } },
    { httpRequest: { status: 500 }, textPayload: 'pymongo ServerSelectionTimeout', severity: 'ERROR' }]);
  assert.equal(report.classes.http_5xx, 2);
  assert.equal(report.classes.mongo_selection, 1);
});
test('successful MongoDB informational logs and numbers in text are not HTTP failures', () => {
  const report = summarize([{ severity: 'INFO', textPayload: 'MongoDB connected port 500' }]);
  assert.ok(Object.values(report.classes).every(value => value === 0));
});
test('secret raw logs are never returned by the summary', () => {
  const report = summarize([{ textPayload: 'MongoDB error password=private', severity: 'ERROR' }]);
  assert.equal(report.classes.mongo_other, 1);
  assert.ok(!JSON.stringify(report).includes('private'));
});
test('an error on the second page cannot be hidden by a healthy first page', async () => {
  const calls = [];
  const report = await readLogs(async request => {
    calls.push(request);
    return request.pageToken ? { entries: [{ httpRequest: { status: 503 } }] }
      : { entries: [{ httpRequest: { status: 200 } }], nextPageToken: 'second' };
  }, options);
  assert.equal(calls[1].pageToken, 'second');
  assert.equal(calls[0].filter, calls[1].filter);
  assert.equal(report.pages, 2);
  assert.equal(report.complete, true);
  assert.equal(report.status, 'errors_observed');
  assert.equal(report.classes.http_5xx, 1);
});
test('page limit produces incomplete evidence, not a clean bill of health', async () => {
  const report = await readLogs(async () => ({ entries: [], nextPageToken: 'more' }), { ...options, maxPages: 1 });
  assert.equal(report.status, 'incomplete');
  assert.equal(report.complete, false);
});
test('empty result is explicitly unobserved', async () => {
  const report = await readLogs(async () => ({}), options);
  assert.equal(report.status, 'no_observations');
});
test('API failure and repeated token do not yield successful evidence', async () => {
  await assert.rejects(readLogs(async () => { throw new Error('HTTP 403'); }, options));
  await assert.rejects(readLogs(async () => ({ nextPageToken: 'same' }), options), /Repeated/);
});
test('invalid timestamps and revision filter injection are rejected before requesting', async () => {
  const request = () => { throw new Error('should not fetch'); };
  await assert.rejects(readLogs(request, { after: 'bad' }), /timestamp/);
  await assert.rejects(readLogs(request, { ...options, revision: 'vibecart-web-x" OR true' }), /revision/);
});

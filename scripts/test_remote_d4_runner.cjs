const test = require('node:test');
const assert = require('node:assert/strict');
const { selectedRevision, assertDeployment, temporaryBinding, removeOurBinding } =
  require('./run_remote_d4_consumer_probe.cjs');

test('uses serving revision, excludes zero traffic previews and latest ready', () => {
  assert.equal(selectedRevision({ latestReadyRevision: 'untested', trafficStatuses: [
    { revision: 'preview' }, { revision: 'serving', percent: 100 },
  ] }), 'serving');
  assert.throws(() => selectedRevision({ trafficStatuses: [
    { revision: 'a', percent: 90 }, { revision: 'b', percent: 10 },
  ] }));
});

const sa = 'vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com';
const production = { image: 'registry/web@sha256:' + 'a'.repeat(64) };
function acceptance() {
  return { image: production.image, serviceAccount: sa, env: [
    { name: 'CLOUD_ACCEPTANCE_MODE', value: 'true' },
    { name: 'CLOUD_ACCEPTANCE_DB', value: 'vibecart_acceptance_pr21' },
    { name: 'CLOUD_PREVIEW_READ_ONLY', value: 'false' },
  ] };
}
const policy = { bindings: [{ role: 'roles/run.invoker', members: ['serviceAccount:' + sa] }] };
test('requires same pinned image, isolated database and private invoker', () => {
  assert.doesNotThrow(() => assertDeployment(production, acceptance(), policy));
  assert.throws(() => assertDeployment(production, { ...acceptance(), image: 'web:latest' }, policy));
  const wrong = acceptance(); wrong.env[1].value = 'vibecart_ai';
  assert.throws(() => assertDeployment(production, wrong, policy));
  assert.throws(() => assertDeployment(production, acceptance(), {
    bindings: [{ role: 'roles/run.invoker', members: ['allUsers'] }],
  }));
});
test('revokes only its own conditional grant and preserves concurrent policy', () => {
  const ours = temporaryBinding('sam-unique', '2026-10-18T01:00:00Z');
  assert.equal(ours.role, 'roles/iam.serviceAccountOpenIdTokenCreator');
  assert.match(ours.condition.expression, /request.time < timestamp/);
  const concurrent = { ...ours, members: ['user:other@example.invalid'] };
  const base = { version: 3, etag: 'current-etag', bindings: [ours, concurrent,
    { role: 'roles/viewer', members: ['user:other@example.invalid'] }] };
  const updated = removeOurBinding(base, ours);
  assert.equal(updated.etag, 'current-etag');
  assert.deepEqual(updated.bindings, base.bindings.slice(1));
  assert.equal(base.bindings.length, 3);
});

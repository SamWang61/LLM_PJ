const test = require('node:test');
const assert = require('node:assert/strict');
const runner = require('./run_remote_transaction_acceptance_probe.cjs');

test('D4-only replay selects the fixed consumer without replaying successful member writes', () => {
  const mode = runner.probeMode(['--run-d4-only-isolated']);
  assert.equal(mode.run, true);
  assert.equal(mode.python, 'remote_d4_consumer_probe.py');
  assert.equal(mode.d4Only, true);
  assert.equal(mode.h05h07, false);
  assert.equal(mode.accounts, false);
  assert.equal(mode.prefix, 'sam-d4-only-');
  assert.throws(() => runner.probeMode(['--run-d4-only-isolated', '--run-isolated']));
});

test('default never grants IAM or starts account writes', () => {
  assert.equal(runner.probeMode([]).run, false);
  assert.equal(runner.probeMode(['--run-isolated']).python, 'remote_transaction_acceptance_probe.py');
  const accounts = runner.probeMode(['--run-accounts-isolated']);
  assert.equal(accounts.run, true);
  assert.equal(accounts.python, 'remote_account_acceptance_probe.py');
  assert.equal(accounts.prefix, 'sam-accounts-');
  assert.throws(() => runner.probeMode(['--run-accounts-isolated', '--production']));
  assert.throws(() => runner.probeMode(['../arbitrary.py']));
});

test('account runner rejects public or mixed invokers before credential use', () => {
  const sa = 'vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com';
  const image = 'registry/web@sha256:' + 'a'.repeat(64);
  const acceptance = { image, serviceAccount: sa, env: [
    { name: 'CLOUD_ACCEPTANCE_MODE', value: 'true' },
    { name: 'CLOUD_ACCEPTANCE_DB', value: 'vibecart_acceptance_pr21' },
    { name: 'CLOUD_PREVIEW_READ_ONLY', value: 'false' },
  ] };
  assert.throws(() => runner.assertDeployment({ image }, acceptance, {
    bindings: [{ role: 'roles/run.invoker', members: ['serviceAccount:' + sa, 'allUsers'] }],
  }));
  assert.throws(() => runner.assertDeployment({ image: image.slice(0, -64) + 'b'.repeat(64) }, acceptance, {
    bindings: [{ role: 'roles/run.invoker', members: ['serviceAccount:' + sa] }],
  }));
});

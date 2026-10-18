const test = require('node:test');
const assert = require('node:assert/strict');
const runner = require('./run_remote_transaction_acceptance_probe.cjs');

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

test('private runner recognizes only the existing SAM maintainer alongside runtime SA', () => {
  const sa = 'vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com';
  const image = 'registry/web@sha256:' + 'a'.repeat(64);
  const acceptance = { image, serviceAccount: sa, env: [
    { name: 'CLOUD_ACCEPTANCE_MODE', value: 'true' },
    { name: 'CLOUD_ACCEPTANCE_DB', value: 'vibecart_acceptance_pr21' },
    { name: 'CLOUD_PREVIEW_READ_ONLY', value: 'false' },
  ] };
  const policy = members => ({ bindings: [{ role: 'roles/run.invoker', members }] });
  assert.doesNotThrow(() => runner.assertDeployment({ image }, acceptance,
    policy(['user:cashsam@gmail.com', 'serviceAccount:' + sa])));
  for (const members of [
    ['serviceAccount:' + sa, 'user:other@example.invalid'],
    ['serviceAccount:' + sa, 'allAuthenticatedUsers'],
    ['serviceAccount:' + sa, 'user:cashsam@gmail.com', 'allUsers'],
    ['user:cashsam@gmail.com'],
  ]) assert.throws(() => runner.assertDeployment({ image }, acceptance, policy(members)));
  assert.throws(() => runner.assertDeployment({ image }, acceptance, {
    bindings: [{ role: 'roles/run.invoker', members: ['serviceAccount:' + sa],
      condition: { expression: 'true' } }],
  }));
});

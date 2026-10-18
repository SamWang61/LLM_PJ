const test = require('node:test');
const assert = require('node:assert/strict');
const r = require('./run_remote_transaction_acceptance_probe.cjs');
const sa = 'serviceAccount:vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com';
const maintainer = 'user:cashsam@gmail.com';
const image = 'registry/web@sha256:' + 'a'.repeat(64);
const target = { image, serviceAccount: sa.split(':')[1], env: [
  { name: 'CLOUD_ACCEPTANCE_MODE', value: 'true' },
  { name: 'CLOUD_ACCEPTANCE_DB', value: 'vibecart_acceptance_pr21' },
  { name: 'CLOUD_PREVIEW_READ_ONLY', value: 'false' },
] };
const policy = members => ({ bindings: [{ role: 'roles/run.invoker', members }] });
test('H05-H07 opts in to one fixed probe pair and private maintainer identity', () => {
  const mode = r.probeMode(['--run-h05-h07-isolated']);
  assert.equal(mode.h05h07, true);
  assert.equal(mode.prefix, 'ren-h057-');
  assert.equal(r.probeMode([]).run, false);
  assert.throws(() => r.probeMode(['--run-h05-h07-isolated', '--other']));
  assert.doesNotThrow(() => r.assertDeployment({ image }, target, policy([sa, maintainer]), true));
  assert.doesNotThrow(() => r.assertDeployment({ image }, target, policy([sa]), true));
  assert.throws(() => r.assertDeployment({ image }, target, policy([sa, maintainer])));
});
test('explicit maintainer allowance rejects every public, foreign or conditional invoker', () => {
  for (const members of [[sa, 'allUsers'], [sa, 'allAuthenticatedUsers'],
    [sa, 'user:other@example.invalid'], [maintainer], [sa, sa]]) {
    assert.throws(() => r.assertDeployment({ image }, target, policy(members), true));
  }
  const conditional = policy([sa, maintainer]);
  conditional.bindings[0].condition = { title: 'unexpected' };
  assert.throws(() => r.assertDeployment({ image }, target, conditional, true));
  assert.throws(() => r.assertDeployment({ image: image + 'bad' }, target, policy([sa]), true));
});
test('retry cannot extend the authorized IAM deadline', () => {
  const now = Date.parse('2026-10-18T08:45:00Z');
  assert.equal(r.grantExpiry(now, '2026-10-18T09:01:18Z'), '2026-10-18T09:01:18.000Z');
  for (const invalid of ['invalid', '2026-10-18T08:44:00Z', '2026-10-18T09:06:00Z']) {
    assert.throws(() => r.grantExpiry(now, invalid));
  }
});
test('one-request child flushes its response and exits despite an idle socket-like handle', () => {
  const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
  const { spawnSync } = require('node:child_process');
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ren-https-exit-test-'));
  const preload = path.join(folder, 'fetch.cjs');
  fs.writeFileSync(preload, "global.fetch=async()=>({status:200,headers:new Headers({'Content-Type':'text/plain'}),arrayBuffer:async()=>Uint8Array.from([111,107]).buffer});setInterval(()=>{},1000);");
  try {
    const result = spawnSync(process.execPath, ['--require', preload,
      path.join(__dirname, 'private_https_transport.cjs')], {
      input: JSON.stringify({ url: 'https://vibecart-acceptance-pr21-m44ncgz5ta-de.a.run.app/cart',
        method: 'GET', headers: {Authorization: 'Bearer unused-test-value'} }),
      encoding: 'utf8', timeout: 3000, windowsHide: true,
    });
    assert.equal(result.error, undefined);
    assert.equal(result.status, 0);
    assert.equal(JSON.parse(result.stdout).body_base64, 'b2s=');
    assert.equal(result.stdout.includes('unused-test-value'), false);
  } finally { fs.unlinkSync(preload); fs.rmdirSync(folder); }
});

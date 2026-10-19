// Promote a staged N06 revision after checking pinned image and unchanged service config.
const path = require('node:path');
const fs = require('node:fs');
const { isDeepStrictEqual } = require('node:util');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const production = process.argv.includes('--production');
const barrier = process.argv.includes('--barrier');
if (production && barrier) throw new Error('Barrier is forbidden in production');
const service = production ? 'vibecart-web' : 'vibecart-acceptance-pr21';
const old = production ? 'vibecart-web-n06-1019' : barrier
  ? 'vibecart-acceptance-pr21-n06-294c-1019' : 'vibecart-acceptance-pr21-n06-1019';
const candidate = production ? 'vibecart-web-n06-294c-1019' : barrier
  ? 'vibecart-acceptance-pr21-n06-294c-barrier-1019'
    : 'vibecart-acceptance-pr21-n06-294c-1019';
const image = 'asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:796a42b6d5fd80099900abc381d4c954d21ed1bea162ad0a9a49a89355deb40a';
const sourceSha = '294c1fac26d6785054063b8be6eb7d9e61075be4';
const validate = process.argv.includes('--validate');
const apply = process.argv.includes('--apply');
const rollback = process.argv.includes('--rollback');
if ([validate, apply, rollback].filter(Boolean).length !== 1 || process.argv.length !== ((barrier || production) ? 4 : 3))
  throw new Error('Use exactly --validate, --apply or --rollback, optionally with --barrier or --production');

async function main() {
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    const value = await response.json();
    if (!response.ok) throw new Error(`${method} ${new URL(url).pathname} HTTP ${response.status} ${value.error?.status || ''}`);
    return value;
  }
  const base = `https://run.googleapis.com/v2/projects/vibecart-llmai/locations/asia-east1/services/${service}`;
  const before = await api(base);
  const active = (before.trafficStatuses || []).filter(x => x.percent);
  const from = rollback ? candidate : old;
  const target = rollback ? old : candidate;
  if (active.length !== 1 || active[0].percent !== 100 || active[0].revision !== from)
    throw new Error('Unexpected current 100% revision; refusing rollout');
  if (!before.latestReadyRevision?.endsWith('/' + candidate))
    throw new Error('Candidate revision is not ready');
  const [a, b] = await Promise.all([
    api(`${base}/revisions/${old}`), api(`${base}/revisions/${candidate}`),
  ]);
  if (b.containers?.[0]?.image !== image || b.labels?.['codex-source-sha'] !== sourceSha
    || b.vpcAccess?.egress !== 'ALL_TRAFFIC'
    || b.vpcAccess?.networkInterfaces?.[0]?.network !== 'vibecart-egress-20261019')
    throw new Error('Candidate image, source or fixed-egress configuration mismatch');
  for (const key of ['scaling', 'timeout', 'serviceAccount',
    'maxInstanceRequestConcurrency', 'volumes', 'executionEnvironment', 'sessionAffinity', 'vpcAccess']) {
    if (JSON.stringify(a[key] || null) !== JSON.stringify(b[key] || null))
      throw new Error(`Non-image configuration mismatch: ${key}`);
  }
  const withoutImage = c => c.map(x => ({...x, image: null,
    ...(barrier ? {command: null, args: null} : {})}));
  if (!isDeepStrictEqual(withoutImage(a.containers), withoutImage(b.containers)))
    throw new Error('Container environment, command or arguments changed');
  if (barrier && (JSON.stringify(b.containers[0].command) !== JSON.stringify(['python', '-c'])
    || b.containers[0].args?.[0] !== fs.readFileSync(path.join(__dirname,
      'remote_checkout_barrier_bootstrap.py'), 'utf8')))
    throw new Error('Private barrier wrapper mismatch');
  const flags = Object.fromEntries(b.containers[0].env.filter(x => x.value).map(x => [x.name, x.value]));
  if (!production && (flags.CLOUD_ACCEPTANCE_MODE !== 'true'
    || flags.CLOUD_ACCEPTANCE_DB !== 'vibecart_acceptance_pr21'
    || flags.CLOUD_PREVIEW_READ_ONLY !== 'false'))
    throw new Error('Private acceptance flags mismatch');
  if (production && (flags.CLOUD_ACCEPTANCE_MODE || flags.CLOUD_ACCEPTANCE_DB))
    throw new Error('Acceptance flags present in production');
  const traffic = (before.traffic || []).map(x => {
    if (x.revision === target) return {...x, percent: 100};
    if (x.percent) { const row = {...x}; delete row.percent; return row; }
    return x;
  });
  if (!traffic.some(x => x.revision === target && x.percent === 100))
    throw new Error('Target revision missing from traffic list');
  const op = await api(`${base}?updateMask=traffic&validateOnly=${validate}`, 'PATCH',
    {name: before.name, etag: before.etag, traffic});
  if (!validate) {
    for (let i = 0; i < 36; i++) {
      const state = i === 0 ? op : await api(`https://run.googleapis.com/v2/${op.name}`);
      if (state.done) {
        if (state.error) throw new Error(`Cloud Run rollout failed ${state.error.code}`);
        break;
      }
      if (i === 35) throw new Error('Cloud Run rollout still pending');
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    const after = await api(base);
    const actual = (after.trafficStatuses || []).filter(x => x.percent);
    if (actual.length !== 1 || actual[0].percent !== 100 || actual[0].revision !== target)
      throw new Error('Post-rollout traffic mismatch');
  }
  console.log(JSON.stringify({status: validate ? 'validated' : rollback ? 'rolled-back' : 'promoted',
    checked_at: new Date().toISOString(), service, from, target, image,
    source_sha: sourceSha, fixed_egress: 'vibecart-egress-20261019'}));
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

// Stage the main-CI-approved N06 image on the isolated private acceptance service.
// The currently serving revision keeps all traffic; this script never changes IAM or Atlas.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const fs = require('node:fs');

const project = 'vibecart-llmai';
const region = 'asia-east1';
const production = process.argv.includes('--production');
const barrier = process.argv.includes('--barrier');
if (production && barrier) throw new Error('Barrier is forbidden in production');
const serviceId = production ? 'vibecart-web' : 'vibecart-acceptance-pr21';
const revisionId = production ? 'vibecart-web-n06-294c-1019'
  : barrier ? 'vibecart-acceptance-pr21-n06-294c-barrier-1019'
    : 'vibecart-acceptance-pr21-n06-294c-1019';
const tag = barrier ? 'n06-294c-barrier' : 'n06-294c';
const sourceSha = '294c1fac26d6785054063b8be6eb7d9e61075be4';
const image = 'asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:796a42b6d5fd80099900abc381d4c954d21ed1bea162ad0a9a49a89355deb40a';
const name = `https://run.googleapis.com/v2/projects/${project}/locations/${region}/services/${serviceId}`;
const apply = process.argv.includes('--apply');
const validate = process.argv.includes('--validate');
if (apply === validate || process.argv.length !== ((production || barrier) ? 4 : 3))
  throw new Error('Use --validate or --apply, optionally with --production or --barrier');

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
  const before = await api(name);
  const active = (before.trafficStatuses || []).filter(x => x.percent);
  if (active.length !== 1 || active[0].percent !== 100) throw new Error('Single serving 100% revision required');
  if ((before.traffic || []).some(x => x.revision === revisionId || x.tag === tag))
    throw new Error('N06 candidate already exists; inspect without replacing');
  const serving = active[0].revision;
  const revision = await api(`${name}/revisions/${serving}`);
  if (revision.containers?.length !== 1 || !revision.containers[0].image?.includes('@sha256:')
    || revision.vpcAccess?.egress !== 'ALL_TRAFFIC'
    || revision.vpcAccess?.networkInterfaces?.[0]?.network !== 'vibecart-egress-20261019')
    throw new Error('Current private image or fixed VPC does not match expectations');
  const template = {};
  for (const key of ['scaling', 'timeout', 'serviceAccount', 'containers',
    'maxInstanceRequestConcurrency', 'volumes', 'executionEnvironment', 'sessionAffinity', 'vpcAccess']) {
    if (revision[key] !== undefined) template[key] = revision[key];
  }
  template.containers = structuredClone(revision.containers);
  template.containers[0].image = image;
  if (barrier) {
    if (revision.containers[0].image !== image)
      throw new Error('Barrier source must already serve the N06 image');
    template.containers[0].command = ['python', '-c'];
    template.containers[0].args = [fs.readFileSync(path.join(__dirname,
      'remote_checkout_barrier_bootstrap.py'), 'utf8')];
  }
  template.labels = Object.fromEntries(Object.entries(revision.labels || {})
    .filter(([key]) => key !== 'managed-by'));
  template.labels['codex-source-sha'] = sourceSha;
  template.revision = revisionId;
  const traffic = [...(before.traffic || []), {
    type: 'TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION', revision: revisionId, tag,
  }];
  const op = await api(`${name}?updateMask=template,traffic&validateOnly=${validate}`,
    'PATCH', { name: before.name, etag: before.etag, template, traffic });
  if (validate) {
    if (op.error) throw new Error(`Validation failed ${op.error.code}`);
    console.log(JSON.stringify({ status: 'validated', revision: revisionId,
      image, source_sha: sourceSha, serving_unchanged: serving }));
    return;
  }
  for (let i = 0; i < 48; i++) {
    const state = i === 0 ? op : await api(`https://run.googleapis.com/v2/${op.name}`);
    if (state.done) {
      if (state.error) throw new Error(`Cloud Run operation failed ${state.error.code}`);
      break;
    }
    if (i === 47) throw new Error('Cloud Run operation timed out');
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  const after = await api(name);
  const staged = await api(`${name}/revisions/${revisionId}`);
  const actual = (after.trafficStatuses || []).filter(x => x.percent);
  if (actual.length !== 1 || actual[0].revision !== serving || actual[0].percent !== 100
    || staged.containers?.[0]?.image !== image
    || staged.labels?.['codex-source-sha'] !== sourceSha
    || staged.vpcAccess?.egress !== 'ALL_TRAFFIC'
    || (barrier && JSON.stringify(staged.containers[0].command) !== JSON.stringify(['python', '-c']))
    || !(after.trafficStatuses || []).some(x => x.revision === revisionId && x.tag === tag && !x.percent))
    throw new Error('Candidate or unchanged serving traffic readback mismatch');
  console.log(JSON.stringify({ status: 'staged-zero-traffic', checked_at: new Date().toISOString(),
    revision: revisionId, image, source_sha: sourceSha, serving_unchanged: serving,
    fixed_vpc: staged.vpcAccess.networkInterfaces[0].network }));
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

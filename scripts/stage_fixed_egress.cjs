// N13: stage the currently serving image/config on fixed NAT at zero traffic.
// Does not change IAM, Atlas, secrets or the current 100% revision.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai', region = 'asia-east1';
const network = 'vibecart-egress-20261019', subnet = 'vibecart-egress-subnet';
const expectedIp = '35.229.228.204';
const serviceId = process.argv.includes('--private') ? 'vibecart-acceptance-pr21'
  : process.argv.includes('--production') ? 'vibecart-web' : null;
const revisionId = serviceId === 'vibecart-web' ? 'vibecart-web-nat-1019'
  : 'vibecart-acceptance-pr21-nat-1019';
const tag = 'nat-1019';
const base = `https://run.googleapis.com/v2/projects/${project}/locations/${region}`;
function requireValue(value, message) { if (!value) throw new Error(message); }
async function main() {
  requireValue(serviceId && (process.argv.includes('--validate') || process.argv.includes('--apply')),
    'Use --private or --production with --validate or --apply');
  const account = auth.getGlobalDefaultAccount();
  requireValue(account?.user?.email === 'cashsam@gmail.com' && account.tokens?.refresh_token,
    'Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    const value = await response.json();
    if (!response.ok) throw new Error(`${method} ${new URL(url).pathname} HTTP ${response.status} ${value.error?.status || ''} ${(value.error?.details || []).map(x => x.reason).filter(Boolean).join(',')}`);
    return value;
  }
  async function waitOperation(operation) {
    requireValue(operation.name, 'Cloud Run operation name missing');
    if (operation.done) {
      requireValue(!operation.error, `Cloud Run operation failed: ${operation.error?.code}`);
      return operation.response;
    }
    for (let attempt = 0; attempt < 48; ++attempt) {
      const state = await api(`https://run.googleapis.com/v2/${operation.name}`);
      if (state.done) {
        requireValue(!state.error, `Cloud Run operation failed: ${state.error?.code} ${state.error?.message || ''}`);
        return state.response;
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    throw new Error('Cloud Run operation did not complete in 240 seconds');
  }
  const address = await api(`https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/addresses/vibecart-egress-ip`);
  const router = await api(`https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/routers/vibecart-egress-router`);
  const nat = router.nats?.find(n => n.name === 'vibecart-egress-nat');
  requireValue(address.address === expectedIp && address.status === 'IN_USE'
    && nat?.natIpAllocateOption === 'MANUAL_ONLY' && nat.natIps?.[0] === address.selfLink,
    'Reserved NAT IP is not attached as expected');
  const name = `${base}/services/${serviceId}`;
  const before = await api(name);
  const active = (before.trafficStatuses || []).filter(x => x.percent);
  requireValue(active.length === 1 && active[0].percent === 100,
    'Exactly one serving 100% revision is required');
  const serving = active[0].revision;
  requireValue(!(before.traffic || []).some(x => x.revision === revisionId || x.tag === tag),
    'NAT revision or tag already exists; inspect it instead of overwriting');
  const revision = await api(`${name}/revisions/${serving}`);
  requireValue(revision.containers?.length === 1 && revision.containers[0].image?.includes('@sha256:'),
    'Serving image must be pinned by digest');
  const template = {};
  for (const key of ['scaling', 'timeout', 'serviceAccount', 'containers',
      'maxInstanceRequestConcurrency', 'volumes', 'executionEnvironment', 'sessionAffinity']) {
    if (revision[key] !== undefined) template[key] = revision[key];
  }
  template.labels = Object.fromEntries(Object.entries(revision.labels || {})
    .filter(([key]) => !['managed-by'].includes(key)));
  template.revision = revisionId;
  template.vpcAccess = { networkInterfaces: [{ network, subnetwork: subnet }],
    egress: 'ALL_TRAFFIC' };
  const traffic = [...(before.traffic || []), {
    type: 'TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION', revision: revisionId, tag,
  }];
  const body = { name: before.name, etag: before.etag, template, traffic };
  const url = `${name}?updateMask=template,traffic&validateOnly=${process.argv.includes('--validate')}`;
  const operation = await api(url, 'PATCH', body);
  if (process.argv.includes('--validate')) {
    process.stdout.write(JSON.stringify({ validation_operation: operation.name,
      done: operation.done || false, error_code: operation.error?.code || null,
      metadata_fields: Object.keys(operation.metadata || {}),
      response_fields: Object.keys(operation.response || {}) }) + '\n');
    return;
  }
  await waitOperation(operation);
  const after = await api(name);
  const actualActive = (after.trafficStatuses || []).filter(x => x.percent);
  requireValue(actualActive.length === 1 && actualActive[0].revision === serving
    && actualActive[0].percent === 100, 'Serving traffic changed unexpectedly');
  if (process.argv.includes('--apply')) {
    requireValue(after.latestReadyRevision?.endsWith(`/${revisionId}`),
      'NAT preview revision did not become ready');
    const staged = await api(`${name}/revisions/${revisionId}`);
    requireValue(staged.containers[0].image === revision.containers[0].image
      && staged.vpcAccess?.egress === 'ALL_TRAFFIC'
      && staged.vpcAccess.networkInterfaces?.[0]?.network === network,
      'Staged image or fixed-egress readback mismatch');
    requireValue((after.trafficStatuses || []).some(x => x.revision === revisionId
      && x.tag === tag && !x.percent), 'NAT revision did not receive zero-traffic tag');
  }
  process.stdout.write(JSON.stringify({checked_at: new Date().toISOString(),
    mode: process.argv.includes('--apply') ? 'staged-zero-traffic' : 'validated-only',
    service: serviceId, previous_100_percent_revision: serving,
    current_100_percent_revision: actualActive[0].revision,
    staged_revision: process.argv.includes('--apply') ? revisionId : null,
    image: revision.containers[0].image, expected_nat_ip: expectedIp,
    traffic_changed: false}) + '\n');
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

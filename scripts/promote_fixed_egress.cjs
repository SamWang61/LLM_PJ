// N13: promote staged fixed-egress revision only after same-config checks.
// --rollback restores the previous revision if a post-promotion check fails.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai', region = 'asia-east1';
const privateService = process.argv.includes('--private');
const serviceId = privateService ? 'vibecart-acceptance-pr21' : 'vibecart-web';
const staged = privateService ? 'vibecart-acceptance-pr21-nat-1019' : 'vibecart-web-nat-1019';
const old = privateService ? 'vibecart-acceptance-pr21-00011-2hq' : 'vibecart-web-reviews-b038aaca';
const name = `projects/${project}/locations/${region}/services/${serviceId}`;
const base = `https://run.googleapis.com/v2/${name}`;
function requireValue(value, message) { if (!value) throw new Error(message); }
async function main() {
  const validate = process.argv.includes('--validate');
  const apply = process.argv.includes('--apply');
  const rollback = process.argv.includes('--rollback');
  requireValue([validate, apply, rollback].filter(Boolean).length === 1,
    'Pass exactly one of --validate, --apply, --rollback');
  const account = auth.getGlobalDefaultAccount();
  requireValue(account?.user?.email === 'cashsam@gmail.com' && account.tokens?.refresh_token,
    'Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    const result = await response.json();
    if (!response.ok) throw new Error(`${method} ${new URL(url).pathname} HTTP ${response.status} ${result.error?.status || ''}`);
    return result;
  }
  const service = await api(base);
  const live = (service.trafficStatuses || []).filter(x => x.percent);
  requireValue(live.length === 1 && live[0].percent === 100
    && live[0].revision === (rollback ? staged : old),
    'Unexpected live traffic; refusing to overwrite another rollout');
  const original = await api(`${base}/revisions/${old}`);
  const candidate = await api(`${base}/revisions/${staged}`);
  for (const key of ['scaling', 'timeout', 'serviceAccount', 'containers',
      'maxInstanceRequestConcurrency', 'volumes', 'executionEnvironment', 'sessionAffinity']) {
    requireValue(JSON.stringify(original[key] || null) === JSON.stringify(candidate[key] || null),
      `Non-network revision config differs: ${key}`);
  }
  requireValue(candidate.vpcAccess?.egress === 'ALL_TRAFFIC'
    && candidate.vpcAccess.networkInterfaces?.[0]?.network === 'vibecart-egress-20261019'
    && candidate.vpcAccess.networkInterfaces?.[0]?.subnetwork === 'vibecart-egress-subnet',
    'Candidate fixed-egress config missing');
  const target = rollback ? old : staged;
  const traffic = (service.traffic || []).map(x => {
    if (x.revision === target) return { ...x, percent: 100 };
    if (x.percent) { const row = { ...x }; delete row.percent; return row; }
    return x;
  });
  requireValue(traffic.some(x => x.revision === target && x.percent === 100),
    'Target revision not in service traffic');
  const operation = await api(`${base}?updateMask=traffic&validateOnly=${validate}`,
    'PATCH', {name, etag: service.etag, traffic});
  if (!validate) {
    for (let i = 0; i < 36; ++i) {
      const current = await api(`https://run.googleapis.com/v2/${operation.name}`);
      if (current.done) {
        requireValue(!current.error, `Traffic update failed: ${current.error?.code}`);
        break;
      }
      if (i === 35) throw new Error('Traffic update still pending');
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    const after = await api(base);
    const active = (after.trafficStatuses || []).filter(x => x.percent);
    requireValue(active.length === 1 && active[0].percent === 100
      && active[0].revision === target, 'Traffic readback did not match target');
  }
  process.stdout.write(JSON.stringify({ checked_at: new Date().toISOString(),
    service: serviceId, mode: validate ? 'validated-only' : rollback ? 'rolled-back' : 'promoted',
    from_revision: live[0].revision, target_100_percent_revision: target,
    image: original.containers[0].image, non_network_configuration_equal: true,
    candidate_vpc: candidate.vpcAccess, source_sha: original.labels?.['codex-source-sha']}) + '\n');
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

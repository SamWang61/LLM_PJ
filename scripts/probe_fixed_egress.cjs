// Ephemeral no-secret Cloud Run Job proves public source IP for N13.
// It never touches Atlas. It removes only the job created by this script.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai', region = 'asia-east1';
const jobId = 'sam-egress-probe-20261019';
const jobName = `projects/${project}/locations/${region}/jobs/${jobId}`;
const runBase = `https://run.googleapis.com/v2/projects/${project}/locations/${region}`;
const expectedIp = '35.229.228.204';
const network = 'vibecart-egress-20261019', subnet = 'vibecart-egress-subnet';
function requireValue(value, message) { if (!value) throw new Error(message); }
async function main() {
  const account = auth.getGlobalDefaultAccount();
  requireValue(account?.user?.email === 'cashsam@gmail.com' && account.tokens?.refresh_token,
    'Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body, missing = false) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    if (missing && response.status === 404) return null;
    const value = await response.json();
    if (!response.ok) throw new Error(`${method} ${new URL(url).pathname} HTTP ${response.status} ${value.error?.status || ''} ${(value.error?.details || []).map(x => x.reason).filter(Boolean).join(',')}`);
    return value;
  }
  async function waitOperation(operation, seconds = 180) {
    requireValue(operation.name, 'Cloud Run operation name unavailable');
    for (let i = 0; i < seconds / 5; ++i) {
      const state = await api(`https://run.googleapis.com/v2/${operation.name}`);
      if (state.done) {
        requireValue(!state.error, `Cloud Run operation failed: ${state.error?.code}`);
        return state.response || {};
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    throw new Error(`Cloud Run operation ${operation.name} still pending`);
  }
  const router = await api(`https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/routers/vibecart-egress-router`);
  const nat = router.nats?.find(n => n.name === 'vibecart-egress-nat');
  requireValue(nat?.natIpAllocateOption === 'MANUAL_ONLY' && nat.natIps?.length === 1,
    'Fixed Cloud NAT missing');
  const address = await api(`https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/addresses/vibecart-egress-ip`);
  requireValue(address.address === expectedIp && nat.natIps[0] === address.selfLink,
    'Reserved address or NAT configuration changed');
  let job = await api(`${runBase}/jobs/${jobId}`, 'GET', null, true);
  requireValue(!job, `Probe job ${jobId} already exists; refusing to reuse`);
  const service = await api(`${runBase}/services/vibecart-web`);
  const active = (service.trafficStatuses || []).filter(x => x.percent);
  requireValue(active.length === 1 && active[0].percent === 100, 'Production revision ambiguous');
  const revision = await api(`${runBase}/services/vibecart-web/revisions/${active[0].revision}`);
  const image = revision.containers?.[0]?.image;
  requireValue(/^asia-east1-docker\.pkg\.dev\/vibecart-llmai\/vibecart\/web@sha256:[0-9a-f]{64}$/.test(image),
    'Pinned image unexpected');
  const code = 'import urllib.request; print("EGRESS_IP=" + urllib.request.urlopen("https://api.ipify.org", timeout=15).read().decode().strip(), flush=True)';
  const body = { template: { template: {
    containers: [{ image, command: ['python'], args: ['-c', code] }],
    maxRetries: 0, timeout: '60s',
    vpcAccess: { networkInterfaces: [{ network, subnetwork: subnet }], egress: 'ALL_TRAFFIC' },
  } } };
  let created = false;
  try {
    await waitOperation(await api(`${runBase}/jobs?jobId=${jobId}`, 'POST', body));
    created = true;
    job = await api(`${runBase}/jobs/${jobId}`);
    const vpc = job.template?.template?.vpcAccess;
    requireValue(vpc?.egress === 'ALL_TRAFFIC' && vpc.networkInterfaces?.[0]?.network === network,
      'Probe job VPC readback mismatch');
    const response = await waitOperation(await api(`${runBase}/jobs/${jobId}:run`, 'POST', {}), 240);
    const execution = response.name;
    requireValue(execution?.includes('/executions/'), 'Execution identity unavailable');
    const details = await api(`https://run.googleapis.com/v2/${execution}`);
    requireValue(details.succeededCount === 1 && !details.failedCount,
      'Egress probe execution failed');
    let ip = null;
    for (let attempt = 0; attempt < 12 && !ip; ++attempt) {
      const page = await api('https://logging.googleapis.com/v2/entries:list', 'POST', {
        resourceNames: [`projects/${project}`], pageSize: 100,
        filter: `resource.type="cloud_run_job" AND resource.labels.job_name="${jobId}"`,
        orderBy: 'timestamp desc',
      });
      for (const item of page.entries || []) {
        const match = /^EGRESS_IP=(\d{1,3}(?:\.\d{1,3}){3})\s*$/.exec(item.textPayload || '');
        if (match) { ip = match[1]; break; }
      }
      if (!ip) await new Promise(resolve => setTimeout(resolve, 5000));
    }
    requireValue(ip === expectedIp, `Egress IP mismatch or unreadable: ${ip || 'none'}`);
    process.stdout.write(JSON.stringify({ checked_at: new Date().toISOString(),
      status: 'passed', expected_ip: expectedIp, observed_ip: ip,
      network, subnet, nat: 'vibecart-egress-nat', execution,
      service_changed: false, atlas_changed: false }) + '\n');
  } finally {
    if (created) {
      const current = await api(`${runBase}/jobs/${jobId}`, 'GET', null, true);
      if (current?.name === jobName) {
        await waitOperation(await api(`${runBase}/jobs/${jobId}`, 'DELETE'), 120);
        requireValue(!await api(`${runBase}/jobs/${jobId}`, 'GET', null, true), 'Probe job cleanup failed');
        process.stdout.write('probe_job_removed=true\n');
      }
    }
  }
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

// Read-only N13 inventory. Never print tokens, environment values or secret names.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai';
const region = 'asia-east1';

async function main() {
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token) {
    throw new Error('Expected authenticated Firebase account unavailable');
  }
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function get(label, url) {
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(15000),
      });
      const body = await response.json();
      if (!response.ok) return { label, http: response.status,
        reason: (body.error?.details || []).map(x => x.reason).filter(Boolean),
        status: body.error?.status || null };
      if (label === 'compute-api') return { label, state: body.state };
      if (label === 'billing') return { label, billingEnabled: body.billingEnabled,
        billingAccountLinked: !!body.billingAccountName };
      if (label === 'services') return { label,
        services: (body.services || []).map(s => ({ name: s.name?.split('/').pop(),
          traffic: (s.trafficStatuses || []).filter(t => t.percent).map(t => ({ revision: t.revision, percent: t.percent })),
          vpcAccess: s.template?.vpcAccess || null })), nextPageToken: !!body.nextPageToken };
      if (label === 'jobs') return { label,
        jobs: (body.jobs || []).map(j => ({ name: j.name?.split('/').pop(), vpcAccess: j.template?.vpcAccess || null })),
        nextPageToken: !!body.nextPageToken };
      if (label === 'networks') return { label, networks: (body.items || []).map(n => ({ name: n.name, autoCreateSubnetworks: n.autoCreateSubnetworks })) };
      if (label === 'routers') return { label, routers: (body.items || []).map(x => ({ name: x.name, natNames: (x.nats || []).map(n => n.name) })) };
      if (label === 'addresses') return { label, addresses: (body.items || []).map(x => ({ name: x.name, address: x.address, status: x.status })) };
      if (label === 'permissions') return { label, permissions: body.permissions || [] };
      return { label, http: response.status };
    } catch (error) { return { label, error: error.name }; }
  }
  const base = `https://run.googleapis.com/v2/projects/${project}/locations/${region}`;
  const results = await Promise.all([
    get('compute-api', `https://serviceusage.googleapis.com/v1/projects/${project}/services/compute.googleapis.com`),
    get('billing', `https://cloudbilling.googleapis.com/v1/projects/${project}/billingInfo`),
    get('services', `${base}/services?pageSize=100`),
    get('jobs', `${base}/jobs?pageSize=100`),
    get('networks', `https://compute.googleapis.com/compute/v1/projects/${project}/global/networks`),
    get('routers', `https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/routers`),
    get('addresses', `https://compute.googleapis.com/compute/v1/projects/${project}/regions/${region}/addresses`),
  ]);
  for (const row of results) process.stdout.write(JSON.stringify(row) + '\n');
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

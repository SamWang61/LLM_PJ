// N13 dedicated, manually allocated fixed egress for Cloud Run.
// Creates no Cloud Run revisions and changes no Atlas rules. Run only for
// project vibecart-llmai after reviewing the read-only preflight.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai', region = 'asia-east1';
const names = { network: 'vibecart-egress-20261019', subnet: 'vibecart-egress-subnet',
  address: 'vibecart-egress-ip', router: 'vibecart-egress-router', nat: 'vibecart-egress-nat' };
const base = `https://compute.googleapis.com/compute/v1/projects/${project}`;
const networkUrl = `${base}/global/networks/${names.network}`;
const subnetUrl = `${base}/regions/${region}/subnetworks/${names.subnet}`;
const addressUrl = `${base}/regions/${region}/addresses/${names.address}`;
const routerUrl = `${base}/regions/${region}/routers/${names.router}`;
function requireValue(value, message) { if (!value) throw new Error(message); }

async function main() {
  const account = auth.getGlobalDefaultAccount();
  requireValue(account?.user?.email === 'cashsam@gmail.com' && account.tokens?.refresh_token,
    'Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body, allowMissing = false) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
    if (allowMissing && response.status === 404) return null;
    const value = await response.json();
    if (!response.ok) throw new Error(`${method} ${new URL(url).pathname} HTTP ${response.status} ${value.error?.errors?.[0]?.reason || value.error?.status || ''}`);
    return value;
  }
  async function awaitOperation(operation) {
    requireValue(operation.selfLink, 'Compute operation link unavailable');
    for (let i = 0; i < 36; ++i) {
      const latest = await api(operation.selfLink);
      if (latest.status === 'DONE') {
        requireValue(!latest.error?.errors?.length, `Compute operation ${latest.name} failed: ${latest.error?.errors?.[0]?.code}`);
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    throw new Error(`Compute operation ${operation.name} still pending`);
  }
  const enabled = await api(`https://serviceusage.googleapis.com/v1/projects/${project}/services/compute.googleapis.com`);
  requireValue(enabled.state === 'ENABLED', 'Compute API must be enabled');
  const existing = await Promise.all([networkUrl, subnetUrl, addressUrl, routerUrl].map(u => api(u, 'GET', null, true)));
  if (process.argv.includes('--plan')) {
    process.stdout.write(JSON.stringify({ project, region, names, subnetCidr: '10.91.0.0/24',
      exists: existing.map(Boolean), externalIp: existing[2]?.address || null }) + '\n');
    return;
  }
  requireValue(process.argv.includes('--apply'), 'Pass --plan or --apply');
  let [network, subnet, address, router] = existing;
  if (!network) {
    await awaitOperation(await api(`${base}/global/networks`, 'POST', {
      name: names.network, autoCreateSubnetworks: false, routingConfig: { routingMode: 'REGIONAL' },
      description: 'VibeCart fixed Cloud Run egress; N13 2026-10-19',
    }));
    network = await api(networkUrl);
  }
  requireValue(network.autoCreateSubnetworks === false, 'Unexpected existing network configuration');
  if (!subnet) {
    await awaitOperation(await api(`${base}/regions/${region}/subnetworks`, 'POST', {
      name: names.subnet, network: network.selfLink, ipCidrRange: '10.91.0.0/24',
      privateIpGoogleAccess: true, description: 'VibeCart fixed Cloud Run egress',
    }));
    subnet = await api(subnetUrl);
  }
  requireValue(subnet.network === network.selfLink && subnet.ipCidrRange === '10.91.0.0/24',
    'Unexpected existing subnet configuration');
  if (!address) {
    await awaitOperation(await api(`${base}/regions/${region}/addresses`, 'POST', {
      name: names.address, addressType: 'EXTERNAL', networkTier: 'PREMIUM',
      description: 'VibeCart Atlas allowlist egress; N13 2026-10-19',
    }));
    address = await api(addressUrl);
  }
  requireValue(address.addressType === 'EXTERNAL' && address.networkTier === 'PREMIUM',
    'Unexpected existing address configuration');
  if (!router) {
    await awaitOperation(await api(`${base}/regions/${region}/routers`, 'POST', {
      name: names.router, network: network.selfLink,
      description: 'VibeCart fixed Cloud NAT egress; N13 2026-10-19',
      nats: [{ name: names.nat, natIpAllocateOption: 'MANUAL_ONLY', natIps: [address.selfLink],
        sourceSubnetworkIpRangesToNat: 'LIST_OF_SUBNETWORKS',
        subnetworks: [{ name: subnet.selfLink, sourceIpRangesToNat: ['PRIMARY_IP_RANGE'] }] }],
    }));
    router = await api(routerUrl);
  }
  const nat = router.nats?.find(n => n.name === names.nat);
  requireValue(router.network === network.selfLink && nat?.natIpAllocateOption === 'MANUAL_ONLY'
    && nat.natIps?.length === 1 && nat.natIps[0] === address.selfLink,
    'Unexpected router or NAT configuration');
  process.stdout.write(JSON.stringify({ project, region, network: names.network,
    subnet: names.subnet, nat: names.nat, ip: address.address, addressStatus: address.status,
    cloudRunConfigured: false, atlasAllowlistChanged: false }) + '\n');
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

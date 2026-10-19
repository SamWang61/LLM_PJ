const path = require('node:path');
const { createHash } = require('node:crypto');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
async function main() {
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url) {
    const response = await fetch(url, { signal: AbortSignal.timeout(30000),
      headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error(`Google API HTTP ${response.status}`);
    return response.json();
  }
  const base = 'https://run.googleapis.com/v2/projects/vibecart-llmai/locations/asia-east1/services/';
  for (const id of ['vibecart-acceptance-pr21', 'vibecart-web']) {
    const service = await api(base + id);
    const revisions = [...new Set((service.trafficStatuses || []).map(x => x.revision))];
    const details = await Promise.all(revisions.map(x => api(base + id + '/revisions/' + x)));
    const policy = await api(base + id + ':getIamPolicy?options.requestedPolicyVersion=3');
    console.log(JSON.stringify({service: id, ready: service.latestReadyRevision,
      traffic: service.trafficStatuses, revisions: details.map(d => ({
        revision: d.name.split('/').pop(), image: d.containers?.[0]?.image,
        source_sha: d.labels?.['codex-source-sha'],
        egress: d.vpcAccess?.egress, network: d.vpcAccess?.networkInterfaces?.[0]?.network,
        command: d.containers?.[0]?.command, args_count: d.containers?.[0]?.args?.length,
        first_arg_sha256: d.containers?.[0]?.args?.[0]
          ? createHash('sha256').update(d.containers[0].args[0]).digest('hex') : null,
        service_account: d.serviceAccount,
        env_names: d.containers?.[0]?.env?.map(x => x.name).sort(),
      })), invoker: (policy.bindings || []).filter(b => b.role === 'roles/run.invoker')
        .map(b => ({members: b.members, condition: b.condition?.title || null}))}));
  }
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

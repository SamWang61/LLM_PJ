// Remove the temporary private transaction barrier's tagged route after probe rollback.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
async function main() {
  if (process.argv.length !== 2) throw new Error('No arguments accepted');
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  async function api(url, method = 'GET', body) {
    const response = await fetch(url, { method, signal: AbortSignal.timeout(30000),
      headers: {Authorization: `Bearer ${token}`,
        ...(body ? {'Content-Type': 'application/json'} : {})},
      body: body ? JSON.stringify(body) : undefined});
    const value = await response.json();
    if (!response.ok) throw new Error(`Cloud Run HTTP ${response.status} ${value.error?.status || ''}`);
    return value;
  }
  const url = 'https://run.googleapis.com/v2/projects/vibecart-llmai/locations/asia-east1/services/vibecart-acceptance-pr21';
  const service = await api(url);
  const active = (service.trafficStatuses || []).filter(x => x.percent);
  if (active.length !== 1 || active[0].revision !== 'vibecart-acceptance-pr21-n06-294c-1019'
    || active[0].percent !== 100) throw new Error('Private N06 service is not serving 100%');
  const toRemove = (service.traffic || []).filter(x => x.revision === 'vibecart-acceptance-pr21-n06-294c-barrier-1019'
    || x.tag === 'n06-294c-barrier');
  if (toRemove.length !== 1 || toRemove[0].percent)
    throw new Error('Expected exactly one zero-traffic barrier route');
  const traffic = service.traffic.filter(x => !toRemove.includes(x));
  const op = await api(url + '?updateMask=traffic', 'PATCH',
    {name: service.name, etag: service.etag, traffic});
  for (let i = 0; i < 36; i++) {
    const state = i === 0 ? op : await api('https://run.googleapis.com/v2/' + op.name);
    if (state.done) {
      if (state.error) throw new Error(`Cloud Run cleanup failed ${state.error.code}`);
      break;
    }
    if (i === 35) throw new Error('Cloud Run cleanup still pending');
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  const after = await api(url);
  if ((after.traffic || []).some(x => x.revision === toRemove[0].revision || x.tag === toRemove[0].tag)
    || (after.trafficStatuses || []).filter(x => x.percent).length !== 1
    || (after.trafficStatuses || []).find(x => x.percent)?.revision !== 'vibecart-acceptance-pr21-n06-294c-1019')
    throw new Error('Barrier route or active revision readback mismatch');
  console.log(JSON.stringify({status: 'barrier-tag-removed', checked_at: new Date().toISOString(),
    active_revision: 'vibecart-acceptance-pr21-n06-294c-1019'}));
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

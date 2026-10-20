// Enable the Compute API required by the approved fixed-egress work.
// No network resource is created by this step. No token is printed.
const path = require('node:path');
const auth = require(require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules')],
}));
const project = 'vibecart-llmai';
async function main() {
  const account = auth.getGlobalDefaultAccount();
  if (account?.user?.email !== 'cashsam@gmail.com' || !account.tokens?.refresh_token)
    throw new Error('Expected Firebase CLI account unavailable');
  const token = (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
  const url = `https://serviceusage.googleapis.com/v1/projects/${project}/services/compute.googleapis.com`;
  const get = async (u, method = 'GET') => {
    const response = await fetch(u, { method, headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(30000) });
    const body = await response.json();
    if (!response.ok) throw new Error(`Service Usage HTTP ${response.status} ${body.error?.status || ''}`);
    return body;
  };
  const before = await get(url);
  if (before.state === 'ENABLED') return process.stdout.write('compute.googleapis.com already ENABLED\n');
  const operation = await get(url + ':enable', 'POST');
  process.stdout.write(JSON.stringify({ operation: operation.name, initialDone: !!operation.done }) + '\n');
  if (operation.error) throw new Error(`Enable failed: ${operation.error.code}`);
  for (let i = 0; i < 18; ++i) {
    await new Promise(resolve => setTimeout(resolve, 10000));
    const state = await get(`https://serviceusage.googleapis.com/v1/${operation.name}`);
    if (state.error) throw new Error(`Enable failed: ${state.error.code}`);
    if (state.done) break;
  }
  const after = await get(url);
  process.stdout.write(JSON.stringify({ computeApiState: after.state }) + '\n');
  if (after.state !== 'ENABLED') process.exitCode = 1;
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });

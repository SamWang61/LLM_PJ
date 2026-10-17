// Acquire short-lived Cloud Run and Atlas acceptance credentials in memory only.
const { spawn } = require('node:child_process');
const path = require('node:path');
const firebaseToolsPath = require.resolve('firebase-tools/lib/auth.js', {
  paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules'), process.cwd()],
});
const firebaseAuth = require(firebaseToolsPath);

async function googleJson(url, accessToken, options = {}, stage = 'request') {
  const response = await fetch(url, {
    ...options,
    headers: { Authorization: `Bearer ${accessToken}`, ...(options.headers || {}) },
  });
  if (!response.ok) throw new Error(`Google API ${stage} HTTP ${response.status}`);
  return response.json();
}

async function main() {
  const account = firebaseAuth.getGlobalDefaultAccount();
  if (!account?.tokens?.refresh_token) throw new Error('Firebase CLI login unavailable');
  const credentials = await firebaseAuth.getAccessToken(account.tokens.refresh_token, []);
  const accessToken = credentials.access_token;
  const project = 'vibecart-llmai';
  const location = 'asia-east1';
  const serviceName = 'vibecart-acceptance-pr21';
  const servicePath = `projects/${project}/locations/${location}/services/${serviceName}`;
  const service = await googleJson(`https://run.googleapis.com/v2/${servicePath}`, accessToken, {}, 'service');
  const revision = service.latestReadyRevision?.split('/').pop();
  if (!service.uri || !revision?.startsWith(`${serviceName}-`)) {
    throw new Error('Private Cloud Run revision unavailable');
  }
  const details = await googleJson(`https://run.googleapis.com/v2/${servicePath}/revisions/${revision}`, accessToken, {}, 'revision');
  const image = details.containers?.[0]?.image || service.template?.containers?.[0]?.image;
  if (!image) throw new Error('Private Cloud Run image unavailable');
  const serviceAccount = `vibecart-pr21-acceptance@${project}.iam.gserviceaccount.com`;
  const identity = await googleJson(
    `https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${serviceAccount}:generateIdToken`,
    accessToken, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audience: service.uri, includeEmail: true }),
    }, 'id-token');
  if (!identity.token) throw new Error('Private Cloud Run ID token unavailable');
  const secret = await googleJson(
    `https://secretmanager.googleapis.com/v1/projects/${project}/secrets/vibecart-pr21-acceptance-mongo-uri/versions/1:access`,
    accessToken, {}, 'secret');
  if (!secret.payload?.data) throw new Error('Acceptance Mongo URI unavailable');
  const mongoUri = Buffer.from(secret.payload.data, 'base64').toString('utf8');
  const python = process.env.REN_PYTHON || 'python';
  const child = spawn(python, [path.join(__dirname, 'remote_d4_consumer_probe.py')],
    { stdio: ['pipe', 'pipe', 'pipe'] });
  let output = '';
  child.stdout.on('data', chunk => { output += chunk.toString(); });
  child.stderr.on('data', () => {}); // Never echo traceback containing credential input.
  child.stdin.end(JSON.stringify({ mongo_uri: mongoUri, id_token: identity.token,
    service_url: service.uri, revision, image }));
  const exitCode = await new Promise(resolve => child.on('close', resolve));
  process.stdout.write(output);
  if (exitCode !== 0) process.exitCode = exitCode || 1;
}

main().catch(error => {
  // Google API errors are intentionally reduced to their type/status.
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});

// Fixed-scope Cloud Run transaction probe. Default is read-only;
// --run-isolated permits an expiring ID-token grant and disposable acceptance writes.
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const PROJECT = 'vibecart-llmai';
const LOCATION = 'asia-east1';
const ACCOUNT = 'cashsam@gmail.com';
const SERVICE = 'vibecart-acceptance-pr21';
const SA = 'vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com';
const SA_PATH = 'projects/' + PROJECT + '/serviceAccounts/' + SA;
const ROLE = 'roles/iam.serviceAccountOpenIdTokenCreator';
const MEMBER = 'user:' + ACCOUNT;

function requireValue(ok, message) { if (!ok) throw new Error(message); }
function selectedRevision(service) {
  const active = (service.trafficStatuses || []).filter(t => (t.percent || 0) > 0);
  requireValue(active.length === 1 && active[0].percent === 100 && active[0].revision,
    'Expected exactly one revision with 100 percent traffic');
  return active[0].revision;
}
function assertDeployment(production, acceptance, policy, allowMaintainer = false) {
  requireValue(/@sha256:[a-f0-9]{64}$/.test(production.image)
    && production.image === acceptance.image, 'Pinned deployment images differ');
  const flags = Object.fromEntries((acceptance.env || []).map(e => [e.name, e.value]));
  requireValue(flags.CLOUD_ACCEPTANCE_MODE === 'true'
    && flags.CLOUD_ACCEPTANCE_DB === 'vibecart_acceptance_pr21'
    && flags.CLOUD_PREVIEW_READ_ONLY === 'false', 'Acceptance database mode mismatch');
  const invokers = (policy.bindings || []).filter(b => b.role === 'roles/run.invoker');
  const members = invokers[0]?.members || [];
  const allowed = ['serviceAccount:' + SA, ...(allowMaintainer ? [MEMBER] : [])];
  requireValue(invokers.length === 1 && !invokers[0].condition
    && members.includes('serviceAccount:' + SA)
    && members.length === new Set(members).size
    && members.every(member => allowed.includes(member)), 'Acceptance invoker scope mismatch');
  requireValue(acceptance.serviceAccount === SA, 'Acceptance runtime identity mismatch');
}
function temporaryBinding(title, expires) {
  return { role: ROLE, members: [MEMBER], condition: { title,
    description: 'Isolated acceptance probe; remove immediately after run',
    expression: 'request.time < timestamp("' + expires + '")' } };
}
function grantExpiry(now, deadline) {
  const limit = now + 20 * 60000;
  const expires = deadline ? Date.parse(deadline) : limit;
  requireValue(Number.isFinite(expires) && expires > now && expires <= limit,
    'IAM deadline must be in the next 20 minutes');
  return new Date(expires).toISOString();
}
function removeOurBinding(policy, binding) {
  return { ...policy, bindings: (policy.bindings || []).filter(b =>
    !(b.role === binding.role && b.condition?.title === binding.condition.title
      && b.condition?.expression === binding.condition.expression
      && b.members?.length === 1 && b.members[0] === MEMBER)) };
}
async function credentials() {
  const auth = require(require.resolve('firebase-tools/lib/auth.js', {
    paths: [path.join(process.env.APPDATA || '', 'npm', 'node_modules'), process.cwd()],
  }));
  const account = auth.getGlobalDefaultAccount();
  requireValue(account?.user?.email === ACCOUNT && account.tokens?.refresh_token,
    'Expected Firebase CLI account unavailable');
  return (await auth.getAccessToken(account.tokens.refresh_token, [])).access_token;
}
function googleApi(token) {
  return async (url, options = {}, stage = 'request') => {
    const response = await fetch(url, { ...options, signal: AbortSignal.timeout(30000),
      headers: { Authorization: 'Bearer ' + token, ...(options.headers || {}) } });
    if (!response.ok) {
      const error = new Error('Google API ' + stage + ' HTTP ' + response.status);
      const body = await response.json().catch(() => ({}));
      error.reasons = (body.error?.details || []).map(d => d.reason).filter(Boolean);
      throw error;
    }
    return response.json();
  };
}
async function readDeployment(api, name) {
  const base = 'https://run.googleapis.com/v2/projects/' + PROJECT
    + '/locations/' + LOCATION + '/services/' + name;
  const service = await api(base, {}, 'service');
  const revision = selectedRevision(service);
  const details = await api(base + '/revisions/' + revision, {}, 'revision');
  const policy = await api(base + ':getIamPolicy?options.requestedPolicyVersion=3', {}, 'invoker');
  return { name, uri: service.uri, revision, image: details.containers?.[0]?.image,
    source_sha: details.labels?.['codex-source-sha'] || null,
    serviceAccount: details.serviceAccount, env: details.containers?.[0]?.env, policy };
}
function publicDeployment(d) {
  return { service: d.name, revision: d.revision, traffic_percent: 100,
    image: d.image, source_sha: d.source_sha };
}
async function listAll(api, url, key) {
  const results = [];
  let pageToken;
  do {
    const target = new URL(url);
    if (pageToken) target.searchParams.set('pageToken', pageToken);
    const page = await api(target, {}, 'inventory-' + key + '-' + target.pathname);
    requireValue(!page.unreachable?.length, 'Cloud inventory contains unreachable regions');
    results.push(...(page[key] || []));
    pageToken = page.nextPageToken;
  } while (pageToken);
  return results;
}
async function inventory(api) {
  const [locations, topics, subscriptions, enabled] = await Promise.all([
    listAll(api, 'https://run.googleapis.com/v1/projects/' + PROJECT + '/locations', 'locations'),
    listAll(api, 'https://pubsub.googleapis.com/v1/projects/' + PROJECT + '/topics', 'topics'),
    listAll(api, 'https://pubsub.googleapis.com/v1/projects/' + PROJECT + '/subscriptions', 'subscriptions'),
    listAll(api, 'https://serviceusage.googleapis.com/v1/projects/278483818008/services?filter=state:ENABLED', 'services'),
  ]);
  requireValue(locations.length > 0, 'Cloud Run region inventory is empty');
  const jobs = [], services = [], restricted = [];
  // Check services and Jobs in every returned location rather than wildcard results.
  for (let i = 0; i < locations.length; i += 5) {
    const batch = await Promise.all(locations.slice(i, i + 5).map(async l => {
      const region = 'https://run.googleapis.com/v2/projects/' + PROJECT + '/locations/' + l.locationId;
      const results = await Promise.allSettled([
        listAll(api, region + '/jobs', 'jobs'), listAll(api, region + '/services', 'services'),
      ]);
      for (const result of results) {
        if (result.status === 'rejected'
            && !result.reason.reasons?.includes('LOCATION_POLICY_VIOLATED')) throw result.reason;
      }
      return { jobs: results[0].status === 'fulfilled' ? results[0].value : [],
        services: results[1].status === 'fulfilled' ? results[1].value : [],
        restricted: results.some(r => r.status === 'rejected') ? l.locationId : null };
    }));
    for (const b of batch) {
      jobs.push(...b.jobs); services.push(...b.services);
      if (b.restricted) restricted.push(b.restricted);
    }
  }
  return { services: services.map(s => s.name).sort(), jobs: jobs.map(j => j.name).sort(),
    job_regions_checked: locations.map(l => l.locationId).sort(),
    restricted_regions: restricted.sort(), restricted_reason: 'LOCATION_POLICY_VIOLATED',
    topics: topics.map(t => t.name), subscriptions: subscriptions.map(s => s.name),
    enabled_worker_apis: ['cloudscheduler', 'cloudfunctions', 'workflows', 'cloudtasks']
      .filter(n => enabled.some(s => s.config?.name === n + '.googleapis.com')) };
}
async function getPolicy(api) {
  return api('https://iam.googleapis.com/v1/' + SA_PATH
    + ':getIamPolicy?options.requestedPolicyVersion=3', { method: 'POST' }, 'sa-policy');
}
async function setPolicy(api, policy) {
  return api('https://iam.googleapis.com/v1/' + SA_PATH + ':setIamPolicy', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ policy: { ...policy, version: 3 } }),
  }, 'sa-policy-update');
}
async function revoke(api, binding) {
  const current = await getPolicy(api);
  const remaining = removeOurBinding(current, binding);
  if (remaining.bindings.length !== (current.bindings || []).length) await setPolicy(api, remaining);
  const after = await getPolicy(api);
  requireValue(!(after.bindings || []).some(b => b.condition?.title === binding.condition.title),
    'Temporary IAM grant still present');
  return true;
}
function probeMode(args) {
  requireValue(args.length <= 1 && (!args.length
    || ['--run-isolated', '--run-accounts-isolated', '--run-h05-h07-isolated', '--run-d4-only-isolated'].includes(args[0])),
    'Usage: node scripts/run_remote_transaction_acceptance_probe.cjs [--run-isolated|--run-accounts-isolated|--run-h05-h07-isolated|--run-d4-only-isolated]');
  const accounts = args[0] === '--run-accounts-isolated';
  const h05h07 = args[0] === '--run-h05-h07-isolated';
  const d4Only = args[0] === '--run-d4-only-isolated';
  return { run: args.length === 1, accounts, h05h07, d4Only,
    python: d4Only ? 'remote_d4_consumer_probe.py'
      : accounts ? 'remote_account_acceptance_probe.py' : 'remote_transaction_acceptance_probe.py',
    prefix: d4Only ? 'sam-d4-only-' : h05h07 ? 'ren-h057-' : accounts ? 'sam-accounts-' : 'sam-txn-' };
}
async function runPython(config, pythonFile) {
  const child = spawn(process.env.REN_PYTHON || 'python',
    [path.join(__dirname, pythonFile)], { stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, REN_PRIVATE_HTTP_TRANSPORT: config.http_transport || 'requests' } });
  let output = '';
  child.stdout.on('data', chunk => { output += chunk.toString(); });
  child.stderr.on('data', () => {}); // Never echo credential-related tracebacks.
  child.stdin.on('error', () => {});
  child.stdin.end(JSON.stringify(config));
  const code = await new Promise((resolve, reject) => {
    child.on('error', () => reject(new Error('Probe Python could not start')));
    child.on('close', resolve);
  });
  let report;
  try { report = JSON.parse(output); } catch { throw new Error('Probe JSON report unavailable'); }
  return { code, report };
}
async function main() {
  const args = process.argv.slice(2);
  const mode = probeMode(args);
  const selectivePrivateProbe = mode.h05h07 || mode.d4Only;
  const api = googleApi(await credentials());
  const report = { checked_at: new Date().toISOString(), mode: args.length ? 'isolated-probe' : 'read-only',
    purpose: mode.d4Only ? 'd4-consumer' : mode.accounts ? 'account-lifecycle' : 'transaction', project: PROJECT, status: 'failed' };
  const [production, acceptance] = await Promise.all([
    readDeployment(api, 'vibecart-web'), readDeployment(api, SERVICE),
  ]);
  assertDeployment(production, acceptance, acceptance.policy, selectivePrivateProbe);
  report.production = publicDeployment(production);
  report.acceptance = publicDeployment(acceptance);
  report.inventory = selectivePrivateProbe
    ? { scope: 'existing private transaction/consumer routes only; no worker or D4 import changes', full_inventory_repeated: false }
    : await inventory(api);
  if (!mode.run) { report.status = 'preflight-passed'; console.log(JSON.stringify(report)); return; }
  const binding = temporaryBinding(mode.prefix + randomUUID(),
    grantExpiry(Date.now(), selectivePrivateProbe ? process.env.REN_IAM_DEADLINE : undefined));
  report.iam = { role: ROLE, member: MEMBER, expires: binding.condition.expression,
    title: binding.condition.title, revoked: false };
  let attempted = false;
  try {
    const before = await getPolicy(api);
    attempted = true; // Clean up even when setIamPolicy has an uncertain outcome.
    await setPolicy(api, { ...before, bindings: [...(before.bindings || []), binding] });
    const after = await getPolicy(api);
    requireValue((after.bindings || []).some(b => b.condition?.title === binding.condition.title),
      'Temporary IAM grant readback missing');
    let identity;
    // IAM policy propagation usually takes minutes, not seconds.
    for (let attempt = 0; attempt < 49; attempt++) {
      report.iam.id_token_attempts = attempt + 1;
      try {
        identity = await api('https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/' + SA + ':generateIdToken',
          { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audience: acceptance.uri, includeEmail: true }) }, 'id-token');
        break;
      } catch (error) {
        if (attempt === 48 || !error.reasons?.includes('IAM_PERMISSION_DENIED')) throw error;
        await new Promise(resolve => setTimeout(resolve, 10000));
      }
    }
    requireValue(identity?.token, 'Private Cloud Run ID token unavailable');
    const secret = await api('https://secretmanager.googleapis.com/v1/projects/' + PROJECT
      + '/secrets/vibecart-pr21-acceptance-mongo-uri/versions/1:access', {}, 'secret');
    requireValue(secret.payload?.data, 'Acceptance Mongo URI unavailable');
    const config = { mongo_uri: Buffer.from(secret.payload.data, 'base64').toString('utf8'),
      id_token: identity.token, service_url: acceptance.uri, revision: acceptance.revision, image: acceptance.image,
      http_transport: selectivePrivateProbe ? 'node-fetch' : 'requests' };
    report.http_transport = config.http_transport;
    const result = await runPython(config, mode.python);
    report.probe = result.report;
    requireValue(result.code === 0 && result.report.status === 'passed'
      && result.report.cleanup?.verified === true, 'Remote probe or cleanup failed');
    if (mode.h05h07) {
      const consumer = await runPython(config, 'remote_d4_consumer_probe.py');
      report.consumer = consumer.report;
      requireValue(consumer.code === 0 && consumer.report.status === 'passed'
        && consumer.report.cleanup?.verified === true, 'Remote consumer or cleanup failed');
    }
    const [pAfter, aAfter] = await Promise.all([
      readDeployment(api, 'vibecart-web'), readDeployment(api, SERVICE),
    ]);
    assertDeployment(pAfter, aAfter, aAfter.policy, selectivePrivateProbe);
    requireValue(pAfter.revision === production.revision && aAfter.revision === acceptance.revision,
      'Traffic revision changed during probe');
    report.deployment_after = { production: publicDeployment(pAfter), acceptance: publicDeployment(aAfter) };
    report.status = 'passed';
  } catch (error) { report.error = error.message; report.error_reasons = error.reasons || []; }
  finally {
    if (attempted) {
      try { report.iam.revoked = await revoke(api, binding); }
      catch (error) { report.status = 'iam-cleanup-failed'; report.iam.error = error.message; }
    }
    console.log(JSON.stringify(report));
  }
  if (report.status !== 'passed') process.exitCode = 1;
}
module.exports = { selectedRevision, assertDeployment, temporaryBinding, removeOurBinding, probeMode, grantExpiry };
if (require.main === module) main().catch(error => {
  console.error(error.message); process.exitCode = 1;
});

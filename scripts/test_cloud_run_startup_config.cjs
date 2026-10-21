const test = require('node:test');
const assert = require('node:assert/strict');
const {applyStartupSettings} = require('./cloud_run_startup_config.cjs');

function template() {
  return {metadata: {name: 'old-revision', labels: {'codex-source-sha': 'image-source'}, annotations: {
    'autoscaling.knative.dev/minScale': '0', 'autoscaling.knative.dev/maxScale': '1',
    'run.googleapis.com/vpc-access-egress': 'all-traffic', 'run.googleapis.com/cpu-throttling': 'true'}},
    spec: {containerConcurrency: 20, timeoutSeconds: 180, serviceAccountName: 'existing-runtime',
      containers: [{image: 'registry/image@sha256:pinned', ports: [{containerPort: 8080}],
        env: [{name: 'SECRET_KEY', valueFrom: {secretKeyRef: {name: 'existing-secret', key: '1'}}}],
        resources: {limits: {cpu: '1', memory: '2Gi'}},
        startupProbe: {httpGet: {path: '/health/live', port: 8080}, periodSeconds: 10, timeoutSeconds: 1, failureThreshold: 12}}]}};
}

test('only startup CPU and startup probe change; secrets, image, scaling and routing fields stay exact', () => {
  const before = template(), snapshot = structuredClone(before), after = applyStartupSettings(before);
  assert.deepEqual(before, snapshot);
  assert.equal(after.metadata.annotations['run.googleapis.com/startup-cpu-boost'], 'true');
  const probe = after.spec.containers[0].startupProbe;
  assert.equal(probe.httpGet.path, '/health/ready');
  assert.equal(probe.periodSeconds * probe.failureThreshold, 120);
  assert.ok(probe.timeoutSeconds <= probe.periodSeconds);
  delete after.metadata.annotations['run.googleapis.com/startup-cpu-boost'];
  after.spec.containers[0].startupProbe = before.spec.containers[0].startupProbe;
  assert.deepEqual(after, before);
});

test('reject an unverified multi-container setup or different serving port', () => {
  const multi = template(); multi.spec.containers.push({...multi.spec.containers[0]});
  assert.throws(() => applyStartupSettings(multi), /one application/);
  const port = template(); port.spec.containers[0].ports[0].containerPort = 9090;
  assert.throws(() => applyStartupSettings(port), /8080/);
});

test('refuse to silently change a different minimum-instance cost policy', () => {
  const input = template(); input.metadata.annotations['autoscaling.knative.dev/minScale'] = '1';
  assert.throws(() => applyStartupSettings(input), /zero-minimum/);
});

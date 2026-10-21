'use strict';

const settings = require('../deploy/cold-start-settings.json');

/** Return a scoped template update; callers retain IAM, traffic and image provenance. */
function applyStartupSettings(template) {
  if (!template?.spec?.containers || template.spec.containers.length !== 1) {
    throw new Error('Expected one application container');
  }
  const container = template.spec.containers[0];
  const ports = container.ports || [{containerPort: 8080}];
  if (ports.length !== 1 || ports[0].containerPort !== 8080) {
    throw new Error('Expected the verified HTTP port 8080');
  }
  if (template.metadata?.annotations?.['autoscaling.knative.dev/minScale'] !== '0') {
    throw new Error('This profile requires the existing zero-minimum-instance policy');
  }
  const result = structuredClone(template);
  result.metadata.annotations['run.googleapis.com/startup-cpu-boost'] = String(settings.startupCpuBoost);
  result.spec.containers[0].startupProbe = structuredClone(settings.startupProbe);
  return result;
}

module.exports = {applyStartupSettings};

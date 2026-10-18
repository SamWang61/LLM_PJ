const test = require('node:test');
const assert = require('node:assert/strict');
const runner = require('./run_remote_checkout_fault_probe.cjs');

test('fault runner rejects account-lifecycle certification and arbitrary modes', () => {
  assert.equal(runner.probeMode([]).run, false);
  const fault = runner.probeMode(['--run-isolated']);
  assert.equal(fault.run, true);
  assert.equal(fault.python, 'remote_checkout_fault_probe.py');
  assert.equal(fault.prefix, 'sam-fault-');
  for (const args of [['--run-accounts-isolated'], ['--production'],
                      ['--run-isolated', '--run-accounts-isolated'], ['other.py']]) {
    assert.throws(() => runner.probeMode(args), /run_remote_checkout_fault_probe/);
  }
});

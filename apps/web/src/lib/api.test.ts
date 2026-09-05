import assert from 'node:assert/strict';
import test from 'node:test';

test('api client module exports helpers', async () => {
  const mod = await import('../lib/api');
  assert.equal(typeof mod.fetchHealth, 'function');
  assert.equal(typeof mod.fetchLive, 'function');
});

import assert from 'node:assert/strict';
import test from 'node:test';

test('contracts export paths type module', async () => {
  const mod = await import('./index');
  assert.ok(mod);
});

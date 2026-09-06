import assert from 'node:assert/strict';
import test from 'node:test';

test('ui package exports design system primitives', async () => {
  const mod = await import('./index');
  assert.equal(typeof mod.Button, 'function');
  assert.equal(typeof mod.Input, 'function');
  assert.equal(typeof mod.FindingCard, 'function');
  assert.equal(typeof mod.ConfidenceIndicator, 'function');
  assert.equal(typeof mod.ScreenStateView, 'function');
  assert.equal(typeof mod.Disclaimer, 'function');
  assert.equal(typeof mod.TemplateCard, 'function');
  assert.equal(typeof mod.DocumentViewer, 'function');
  assert.equal(typeof mod.UploadZone, 'function');
});

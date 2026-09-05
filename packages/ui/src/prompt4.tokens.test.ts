import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = join(dirname(fileURLToPath(import.meta.url)));
const tokens = readFileSync(join(root, 'styles/tokens.css'), 'utf8');
const components = readFileSync(join(root, 'styles/components.css'), 'utf8');

function hexLuminance(hex: string): number {
  const h = hex.replace('#', '').trim();
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const r = parseInt(n.slice(0, 2), 16) / 255;
  const g = parseInt(n.slice(2, 4), 16) / 255;
  const b = parseInt(n.slice(4, 6), 16) / 255;
  const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function tokenValue(name: string, css: string): string {
  const match = css.match(new RegExp(`${name}:\\s*([^;]+);`));
  assert.ok(match, `missing token ${name}`);
  return match![1].trim();
}

test('Prompt 4 tokens use Onest, page bg, ink, and 16px body', () => {
  assert.match(tokens, /--dar-font-sans:\s*'Onest'/);
  assert.doesNotMatch(tokens, /Unbounded|Manrope|fonts\.googleapis|fonts\.gstatic/i);
  assert.equal(tokenValue('--dar-color-bg', tokens).toUpperCase(), '#F4F7FB');
  assert.equal(tokenValue('--dar-color-text', tokens).toUpperCase(), '#111827');
  assert.equal(tokenValue('--dar-color-border', tokens).toUpperCase(), '#CBD5E1');
  assert.equal(tokenValue('--dar-topbar-height', tokens), '72px');
  assert.match(tokens, /font-size:\s*16px/);
  assert.match(tokens, /font-weight:\s*500/);
  assert.match(tokens, /line-height:\s*1\.55/);
});

test('Prompt 4 secondary text is not lighter than #475569', () => {
  const floor = hexLuminance('#475569');
  for (const name of ['--dar-color-text-secondary', '--dar-color-text-muted']) {
    const value = tokenValue(name, tokens);
    assert.match(value, /^#([0-9a-fA-F]{6})$/);
    assert.ok(
      hexLuminance(value) <= floor + 0.002,
      `${name}=${value} is lighter than #475569`,
    );
  }
});

test('Prompt 4 buttons are at least 44px and not visually thin', () => {
  assert.match(components, /\.dar-btn\s*\{[^}]*min-height:\s*4[4-8]px/s);
  assert.match(components, /\.dar-btn--sm\s*\{[^}]*min-height:\s*4[4-8]px/s);
  assert.doesNotMatch(components, /min-height:\s*32px/);
  assert.doesNotMatch(components, /min-height:\s*40px/);
});

test('Prompt 4 ships a local Onest variable font file', () => {
  const fontCss = readFileSync(join(root, 'fonts/onest/onest.css'), 'utf8');
  assert.match(fontCss, /Onest/);
  assert.match(fontCss, /woff2/);
  assert.doesNotMatch(fontCss, /fonts\.googleapis|fonts\.gstatic/i);
});

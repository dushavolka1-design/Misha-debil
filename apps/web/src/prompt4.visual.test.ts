import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const srcRoot = dirname(fileURLToPath(import.meta.url));

function read(rel: string): string {
  return readFileSync(join(srcRoot, rel), 'utf8');
}

test('Prompt 4 layout does not load Google Fonts at runtime', () => {
  const layout = read('app/layout.tsx');
  assert.doesNotMatch(layout, /next\/font\/google/);
  assert.doesNotMatch(layout, /fonts\.googleapis|fonts\.gstatic/);
  assert.doesNotMatch(layout, /Unbounded|Manrope/);
});

test('Prompt 4 landing has hierarchy, no emoji, and process illustration', () => {
  const page = read('app/page.tsx');
  assert.doesNotMatch(page, /📄|✍️/);
  assert.match(page, /dar-landing-illustration|DocumentProcessIllustration/);
  assert.match(page, /dar-trust|trust strip|Доверие/i);
  assert.match(page, /dar-step-card/);
  assert.match(page, /dar-security-badge/);
  assert.match(page, /dar-landing-cta/);
});

test('Prompt 4 keeps exactly two primary app sections', () => {
  const shell = read('components/Shell.tsx');
  assert.match(shell, /Анализатор/);
  assert.match(shell, /Генерация/);
  assert.match(shell, /dar-topbar--scrolled|scrolled/);
  assert.equal((shell.match(/MainNavLink/g) ?? []).length >= 2, true);
});

test('Prompt 4 replaces repeating onboarding with compact help', () => {
  const help = read('components/OnboardingPanel.tsx');
  assert.match(help, /<details|dar-help/);
  assert.doesNotMatch(help, /dar-onboarding__list/);
});

test('Prompt 4 source files do not use Unbounded for headings', () => {
  const css = read('styles/app.css');
  assert.doesNotMatch(css, /Unbounded/);
  assert.match(css, /dar-page-title/);
});

test('Prompt 4 generation catalog uses TemplateCard grid, not inline card layout', () => {
  const catalog = read('app/app/forms/FormsCatalogClient.tsx');
  assert.match(catalog, /TemplateCard/);
  assert.match(catalog, /dar-template-grid|dar-chip/);
  assert.doesNotMatch(catalog, /gridTemplateColumns:\s*'repeat\(auto-fill/);
});

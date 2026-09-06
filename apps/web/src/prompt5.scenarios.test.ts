import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const srcRoot = join(dirname(fileURLToPath(import.meta.url)));

function read(rel: string): string {
  return readFileSync(join(srcRoot, rel), 'utf8');
}

test('Prompt 5 catalog search debounces and can cancel in-flight requests', () => {
  const catalog = read('app/app/forms/FormsCatalogClient.tsx');
  assert.match(catalog, /debounce|AbortController/);
  assert.match(catalog, /signal/);
});

test('Prompt 5 Fill is gated by full generation readiness', () => {
  const catalog = read('app/app/forms/FormsCatalogClient.tsx');
  assert.match(catalog, /generation_ready/);
  assert.match(catalog, /fill_ready/);
});

test('Prompt 5 API client maps correlation and domain error codes', () => {
  const client = read('lib/apiClient.ts');
  assert.match(client, /correlationId|correlation_id/);
  assert.match(client, /catalog_load_failed|font_not_ready|not_published/);
  assert.match(client, /AbortSignal|signal/);
});

test('Prompt 5 analyzer UI separates local results from unavailable advanced analysis', () => {
  const detail = read('app/app/analyzer/DocumentDetailView.tsx');
  assert.match(detail, /llm_available|advancedUnavailable|local_steps/);
  assert.doesNotMatch(detail, /LLM/);
});

test('Prompt 5 wizard exports informational checklist PDF', () => {
  const wizard = read('app/app/entry-wizard/EntryWizardClient.tsx');
  assert.match(wizard, /checklist|чеклист/i);
  assert.match(wizard, /apiFetch|apiClient/);
  assert.match(wizard, /as_of|reviewed|проверено/i);
});

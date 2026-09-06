import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { ESLint } from 'eslint';

const cwd = fileURLToPath(new URL('../', import.meta.url));
const eslint = new ESLint({ cwd });

async function messages(source, filePath) {
  const [result] = await eslint.lintText(source, { filePath });
  return result.messages;
}

const reference = '/// <reference path="./.next/types/routes.d.ts" />\n';

test('Next-generated declarations retain their supported path reference', async () => {
  assert.deepEqual(await messages(reference, 'next-env.d.ts'), []);
});

test('path references remain rejected in application declarations', async () => {
  const result = await messages(reference, 'src/reference-regression.d.ts');
  assert.ok(result.some((message) => message.ruleId === '@typescript-eslint/triple-slash-reference'));
});

test('runtime browser global is recognized without disabling undefined-name checks', async () => {
  assert.deepEqual(
    await messages("window.__DOCLY_API__ = 'http://127.0.0.1:8000';\n", 'public/docly-runtime.js'),
    [],
  );
  const typo = await messages("windwo.__DOCLY_API__ = 'bad';\n", 'public/docly-runtime.js');
  assert.ok(typo.some((message) => message.ruleId === 'no-undef'));
});

test('browser global does not leak into Node scripts', async () => {
  const result = await messages('window.__DOCLY_API__ = 1;\n', 'runtime-regression.mjs');
  assert.ok(result.some((message) => message.ruleId === 'no-undef'));
});

test('unused application imports still fail', async () => {
  const result = await messages("import { ApiError } from './lib/apiClient';\n", 'src/unused.ts');
  assert.ok(result.some((message) => message.ruleId === '@typescript-eslint/no-unused-vars'));
});

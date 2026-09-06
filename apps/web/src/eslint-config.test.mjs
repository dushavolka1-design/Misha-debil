import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath, URL } from 'node:url';
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
  assert.ok(
    result.some((message) => message.ruleId === '@typescript-eslint/triple-slash-reference'),
  );
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

test('object rest can omit client options without admitting unused rest values', async () => {
  const omission =
    'export const strip = (options: object) => { const { timeoutMs, ...init } = options; return init; };';
  assert.deepEqual(await messages(omission, 'src/rest.ts'), []);
  const unused =
    'export const strip = (options: object) => { const { timeoutMs, ...init } = options; return timeoutMs; };';
  const result = await messages(unused, 'src/rest.ts');
  assert.ok(result.some((message) => message.ruleId === '@typescript-eslint/no-unused-vars'));
});

test('ordinary underscore-prefixed variables still fail', async () => {
  const result = await messages('const _unused = 1; export {};', 'src/unused.ts');
  assert.ok(result.some((message) => message.ruleId === '@typescript-eslint/no-unused-vars'));
});

test('unused application imports still fail', async () => {
  const result = await messages("import { ApiError } from './lib/apiClient';\n", 'src/unused.ts');
  assert.ok(result.some((message) => message.ruleId === '@typescript-eslint/no-unused-vars'));
});

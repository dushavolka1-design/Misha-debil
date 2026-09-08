import assert from 'node:assert/strict';
import test from 'node:test';
import { buildAccepts, emptyAccepts, parseLegalItems, requiredConsents, validateCredentials } from './authModel';
const docs = [...requiredConsents, 'marketing'].map((consent_id, i) => ({ id: String(i), consent_id, consent_version: 'test-v1', content_hash: 'a'.repeat(64) }));
test('all consent controls start unchecked', () => assert.deepEqual(Object.values(emptyAccepts()), [false, false, false, false]));
test('ordinary PD cannot be bundled with other accepts', () => {
  assert.throws(() => buildAccepts(docs, { ...emptyAccepts(), terms_of_use: true, offer: true }));
});
test('marketing is omitted unless explicitly checked', () => {
  const result = buildAccepts(docs, { ...emptyAccepts(), terms_of_use: true, offer: true, personal_data_processing: true });
  assert.deepEqual(result.map((r) => r.consent_id), [...requiredConsents]);
  assert.ok(result.every((r) => r.content_hash === 'a'.repeat(64) && r.consent_version === 'test-v1'));
});
test('missing required document blocks registration', () => assert.throws(() => parseLegalItems(docs.slice(1))));
test('invalid hashes and duplicate versions are rejected', () => {
  assert.throws(() => parseLegalItems([...docs, docs[0]]));
  assert.throws(() => parseLegalItems(docs.map((d) => ({ ...d, content_hash: 'invalid' }))));
  assert.throws(() => parseLegalItems({ items: docs }));
});
test('explicit marketing needs its own document version', () => assert.throws(() => buildAccepts(docs.slice(0, 3), { terms_of_use: true, offer: true, personal_data_processing: true, marketing: true })));
test('valid synthetic account needs no passport, patronymic or repeated password', () => assert.deepEqual(validateCredentials({ displayName: 'Test User', email: 'example@example.invalid', password: 'ExampleOnly123' }), []));
test('invalid account data returns linked field errors', () => assert.deepEqual(validateCredentials({ displayName: '', email: 'broken', password: 'short' }).map((e) => e.id), ['reg-name', 'reg-email', 'reg-password']));
test('long names and passwords are bounded', () => assert.equal(validateCredentials({ displayName: 'A'.repeat(81), email: 'example@example.invalid', password: 'A1'.repeat(65) }).length, 2));

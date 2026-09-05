import assert from 'node:assert/strict';
import test from 'node:test';

import { checkAnswers, normalizeField, PETITION_PATENT } from './answerChecks';

test('live checks reject RF citizenship, passport typo and dummy card', () => {
  const issues = checkAnswers(
    'worksheet.mvd.patent.application',
    {
      citizenship: 'Российская Федерация',
      identity_doc_kind: 'Пасспорт',
      migration_card_number: '1234567890',
      petition: 'хочу патент',
    },
    { citizenship: { label: 'Гражданство' } },
  );
  const codes = new Set(issues.map((i) => i.code));
  assert.ok(codes.has('citizenship_rf'));
  assert.ok(codes.has('spelling'));
  assert.ok(codes.has('dummy_value'));
  assert.ok(codes.has('petition_wording'));
});

test('normalize fixes passport typo immediately and petition on blur', () => {
  const passport = normalizeField('mvd.patent.application', 'identity_doc_kind', 'Пасспорт');
  assert.equal(passport.value, 'Паспорт');
  assert.match(passport.message || '', /Паспорт/);

  const whileTyping = normalizeField('mvd.patent.application', 'petition', 'хочу патент');
  assert.equal(whileTyping.value, 'хочу патент');

  const onBlur = normalizeField('mvd.patent.application', 'petition', 'хочу патент', { onBlur: true });
  assert.equal(onBlur.value, PETITION_PATENT);
});

test('accepts foreign passport and real migration card', () => {
  const issues = checkAnswers(
    'mvd.patent.application',
    {
      citizenship: 'Республика Узбекистан',
      identity_doc_kind: 'Паспорт',
      identity_doc_series: 'AA',
      identity_doc_number: '7482915',
      migration_card_series: '2518',
      migration_card_number: '4829173',
      petition: PETITION_PATENT,
    },
    { citizenship: { label: 'Гражданство' } },
  );
  assert.equal(issues.filter((i) => i.severity === 'error').length, 0);
});

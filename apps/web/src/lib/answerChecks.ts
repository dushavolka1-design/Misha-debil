export type FieldIssue = { field_id: string; code: string; message: string; severity: 'error' };

export type FieldMeta = { label?: string; required?: boolean };

export const PETITION_PATENT =
  'Прошу оформить патент на осуществление трудовой деятельности в Российской Федерации';

const RF_CITIZENSHIP = /(российск|россия\b|\bрф\b|russian\s+federation|\brussia\b)/i;
const PASSPORT_TYPO = /пасспорт/gi;
const DUMMY_SEQ = /^(?:0123456789|1234567890|9876543210|0{6,}|1{6,}|9{6,})$/;
const JUNK = /^(test|тест|asdf|qwerty|xxx|n\/?a|foo|bar)$/i;

const FOREIGN_WORKER_SLUGS = new Set([
  'mvd.patent.application',
  'mvd.work_notification',
  'mvd.rvp.application',
  'mvd.vnz.application',
  'mvd.invitation.business',
  'mvd.arrival_notice.app4',
  'mvd.stay_extension',
]);

export function catalogSlug(formSlug: string): string {
  return formSlug.replace(/^worksheet\./, '');
}

function fixPassportTypo(value: string): string {
  return value.replace(PASSPORT_TYPO, (src) => {
    if (src === src.toUpperCase()) return 'ПАСПОРТ';
    if (src[0] && src[0] === src[0].toUpperCase()) return 'Паспорт';
    return 'паспорт';
  });
}

export function normalizeField(
  formSlug: string,
  fieldId: string,
  raw: string,
  opts?: { onBlur?: boolean },
): { value: string; message?: string } {
  const original = raw;
  let value = raw.trim();
  if (!value) return { value: raw };
  const slug = catalogSlug(formSlug);
  let message: string | undefined;
  const afterPassport = fixPassportTypo(value);
  if (afterPassport !== value) {
    value = afterPassport;
    message = 'Исправлено написание: «Паспорт».';
  }
  if (fieldId === 'migration_card_series' || fieldId === 'migration_card_number') {
    const digits = value.replace(/\D/g, '');
    if (digits && digits !== value) {
      value = digits;
      message = 'Оставлены только цифры серии и номера.';
    }
  }
  if (opts?.onBlur && slug === 'mvd.patent.application' && fieldId === 'petition') {
    if (!value.toLowerCase().includes('прошу оформить патент')) {
      value = PETITION_PATENT;
      message = 'Подставлена формулировка заявления об оформлении патента.';
    }
  }
  if (value === original) {
    return message ? { value: original, message } : { value: original };
  }
  return message ? { value, message } : { value };
}

export function checkAnswers(
  formSlug: string,
  answers: Record<string, string>,
  fieldSchema?: Record<string, FieldMeta>,
): FieldIssue[] {
  const issues: FieldIssue[] = [];
  const slug = catalogSlug(formSlug);
  const schema = fieldSchema || {};

  for (const [fieldId, raw] of Object.entries(answers)) {
    const value = (raw || '').trim();
    if (!value) continue;
    if (/пасспорт/i.test(value)) {
      issues.push({
        field_id: fieldId,
        code: 'spelling',
        message: 'Напишите «Паспорт», без лишней «с».',
        severity: 'error',
      });
    }
    const compact = value.replace(/\D/g, '');
    if (compact && DUMMY_SEQ.test(compact)) {
      issues.push({
        field_id: fieldId,
        code: 'dummy_value',
        message: 'Похоже на вымышленный номер. Перенесите серию и номер с настоящего документа.',
        severity: 'error',
      });
    }
    if (JUNK.test(value)) {
      issues.push({
        field_id: fieldId,
        code: 'dummy_value',
        message: 'Укажите реальное значение, как в документе.',
        severity: 'error',
      });
    }
  }

  for (const [fieldId, meta] of Object.entries(schema)) {
    const label = (meta.label || '').toLowerCase();
    if (!label.includes('гражданств') && !fieldId.includes('citizenship')) continue;
    const value = (answers[fieldId] || '').trim();
    if (value && FOREIGN_WORKER_SLUGS.has(slug) && RF_CITIZENSHIP.test(value)) {
      issues.push({
        field_id: fieldId,
        code: 'citizenship_rf',
        message:
          'Для этой процедуры заявитель — иностранный гражданин. Гражданство «Российская Федерация» здесь не подходит.',
        severity: 'error',
      });
    }
  }

  if (slug === 'mvd.patent.application') {
    const petition = (answers.petition || '').trim();
    if (petition && !petition.toLowerCase().includes('прошу оформить патент')) {
      issues.push({
        field_id: 'petition',
        code: 'petition_wording',
        message: 'В заявлении должна быть формулировка «прошу оформить патент».',
        severity: 'error',
      });
    }
    const series = (answers.migration_card_series || '').trim();
    const number = (answers.migration_card_number || '').trim();
    if (series && !/^\d{4}$/.test(series)) {
      issues.push({
        field_id: 'migration_card_series',
        code: 'migration_card_format',
        message: 'Серия миграционной карты — 4 цифры, как на карте, без выдуманной последовательности.',
        severity: 'error',
      });
    }
    if (number && !/^\d{7}$/.test(number)) {
      issues.push({
        field_id: 'migration_card_number',
        code: 'migration_card_format',
        message: 'Номер миграционной карты — 7 цифр с бланка карты, не произвольный набор.',
        severity: 'error',
      });
    }
  }

  return issues;
}

export function issueForField(issues: FieldIssue[], fieldId: string): string | undefined {
  return issues.find((i) => i.field_id === fieldId)?.message;
}

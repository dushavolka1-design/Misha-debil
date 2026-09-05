export type LegalItem = { id: string; consent_id: string; consent_version: string; content_hash: string };
export type Credentials = { displayName: string; email: string; password: string };
export type FieldError = { id: string; message: string };
export const requiredConsents = ['terms_of_use', 'offer', 'personal_data_processing'] as const;
export type ConsentId = (typeof requiredConsents)[number] | 'marketing';
export type Accepts = Record<ConsentId, boolean>;
export const emptyAccepts = (): Accepts => ({ terms_of_use: false, offer: false, personal_data_processing: false, marketing: false });

export function validateCredentials(input: Credentials): FieldError[] {
  const errors: FieldError[] = [];
  if (input.displayName.trim().length < 2 || input.displayName.trim().length > 80) errors.push({ id: 'reg-name', message: 'Укажите имя пользователя: от 2 до 80 символов.' });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email.trim())) errors.push({ id: 'reg-email', message: 'Проверьте email, например name@example.com.' });
  if (input.password.length < 10 || input.password.length > 128 || !/[A-Za-zА-Яа-яЁё]/.test(input.password) || !/\d/.test(input.password)) errors.push({ id: 'reg-password', message: 'Нужны 10–128 символов, буква и цифра.' });
  return errors;
}
export function parseLegalItems(value: unknown): LegalItem[] {
  if (!Array.isArray(value)) throw new Error('invalid_legal_documents');
  const seen = new Set<string>();
  for (const item of value) {
    if (!item || typeof item !== 'object' || typeof item.id !== 'string' || typeof item.consent_id !== 'string' || typeof item.consent_version !== 'string' || typeof item.content_hash !== 'string' || !item.id || !item.consent_version || !/^[a-fA-F0-9]{64}$/.test(item.content_hash ?? '') || seen.has(item.consent_id)) throw new Error('invalid_legal_documents');
    seen.add(item.consent_id);
  }
  if (!requiredConsents.every((id) => seen.has(id))) throw new Error('missing_required_documents');
  return value as LegalItem[];
}
export function buildAccepts(items: LegalItem[], accepts: Accepts) {
  const verifiedItems = parseLegalItems(items);
  if (!requiredConsents.every((id) => accepts[id])) throw new Error('required_consents_missing');
  return Object.entries(accepts).filter(([, checked]) => checked).map(([id]) => {
    const doc = verifiedItems.find((item) => item.consent_id === id);
    if (!doc) throw new Error('consent_version_missing');
    return { consent_id: doc.consent_id, consent_version: doc.consent_version, content_hash: doc.content_hash };
  });
}

'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { ScreenStateView, parseScreenState } from '@dar/ui';
import { ApiError, apiFetch } from '../../lib/apiClient';
import { getApiBase } from '../../lib/apiBase';
import { AuthFlow, type RegistrationPayload } from './AuthFlow';

const loadLegal = (signal: AbortSignal) => apiFetch<unknown>('/legal/documents/active', { signal, retries: 0 });
const legalUrl = (id: string) => `${getApiBase()}/legal/documents/${encodeURIComponent(id)}/text`;
const register = async (payload: RegistrationPayload) => {
  await apiFetch('/auth/register', { method: 'POST', retries: 0, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
};
function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return 'Слишком много попыток. Подождите немного и повторите.';
    if (error.status === 401) return 'Не удалось войти. Проверьте имя пользователя и пароль.';
    if (error.status === 400 || error.status === 422) return 'Не удалось принять данные. Проверьте поля и актуальность согласий.';
    if (error.code === 'network' || error.code === 'timeout') return 'Не удалось подтвердить результат запроса. Проверьте подключение и почту перед повторной отправкой.';
  }
  return 'Сервис временно недоступен. Введённые данные сохранены только в этой вкладке. Попробуйте позже.';
}
export default function AuthClient({ mode }: { mode: 'register' | 'login' }) {
  const router = useRouter();
  const params = useSearchParams();
  const state = parseScreenState(params.get('state'));
  async function login(payload: { username: string; password: string }) {
    await apiFetch('/auth/login', { method: 'POST', retries: 0, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    router.push('/app/analyzer');
  }
  return <ScreenStateView state={state} ready={<AuthFlow mode={mode} loadLegal={loadLegal} legalUrl={legalUrl} register={register} login={login} errorMessage={errorMessage} />} />;
}

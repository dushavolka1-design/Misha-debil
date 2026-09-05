'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMemo, useState } from 'react';

import {
  Button,
  FormErrorSummary,
  Input,
  ScreenStateView,
  parseScreenState,
} from '@dar/ui';

import { getApiBase } from '../../../lib/apiBase';

export default function LoginClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const state = parseScreenState(searchParams.get('state'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const errors = useMemo(() => {
    if (!submitted) return [];
    const list: Array<{ id: string; message: string }> = [];
    if (username.trim().length < 2) {
      list.push({ id: 'login-username', message: 'Укажите имя пользователя' });
    }
    if (password.length < 10) {
      list.push({ id: 'login-password', message: 'Пароль не короче 10 символов' });
    }
    return list;
  }, [submitted, username, password]);

  return (
    <div className="dar-content dar-auth-card">
      <h1 className="dar-page-title">Вход</h1>
      <p className="dar-page-lead">Войдите в личный кабинет для анализа документов и генерации шаблонов.</p>
      <ScreenStateView
        state={state}
        ready={
          <form
            className="dar-stack"
            onSubmit={(e) => {
              e.preventDefault();
              setSubmitted(true);
              setServerError(null);
              if (username.trim().length < 2 || password.length < 10) return;
              void fetch(`${getApiBase()}/auth/login`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username.trim(), password }),
              }).then(async (res) => {
                if (!res.ok) {
                  const data = await res.json().catch(() => ({}));
                  setServerError(data?.detail?.detail || 'Неверное имя или пароль');
                  return;
                }
                router.push('/app/analyzer');
              });
            }}
            noValidate
          >
            <FormErrorSummary errors={errors} />
            {serverError ? (
              <p className="dar-field__error" role="alert">
                {serverError}
              </p>
            ) : null}
            <Input
              id="login-username"
              label="Имя пользователя"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={errors.find((x) => x.id === 'login-username')?.message}
            />
            <Input
              id="login-password"
              label="Пароль"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.find((x) => x.id === 'login-password')?.message}
            />
            <Button type="submit">Войти</Button>
            <p>
              Нет аккаунта? <Link href="/auth/register">Регистрация</Link>
            </p>
          </form>
        }
      />
    </div>
  );
}

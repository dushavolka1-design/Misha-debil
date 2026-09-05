'use client';

import Link from 'next/link';
import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import {
  Button,
  Checkbox,
  FormErrorSummary,
  Input,
  ScreenStateView,
  Skeleton,
  parseScreenState,
} from '@dar/ui';

import { getApiBase } from '../../../lib/apiBase';

type LegalItem = {
  id: string;
  consent_id: string;
  consent_version: string;
  content_hash: string;
};

function RegisterForm() {
  const searchParams = useSearchParams();
  const state = parseScreenState(searchParams.get('state'));
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [legal, setLegal] = useState<LegalItem[]>([]);
  const [legalLoadError, setLegalLoadError] = useState<string | null>(null);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptOffer, setAcceptOffer] = useState(false);
  const [acceptPd, setAcceptPd] = useState(false);
  const [acceptMarketing, setAcceptMarketing] = useState(false); // must stay default false
  const [submitted, setSubmitted] = useState(false);
  const [serverMsg, setServerMsg] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    void fetch(`${getApiBase()}/legal/documents/active`, { credentials: 'include' })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: LegalItem[]) => {
        setLegal(Array.isArray(data) ? data : []);
        setLegalLoadError(null);
      })
      .catch(() => {
        setLegal([]);
        setLegalLoadError(
          `Не удалось загрузить документы с API (${getApiBase()}). Проверьте, что API запущен и CORS разрешает этот origin.`,
        );
      });
  }, []);

  const byId = useMemo(() => Object.fromEntries(legal.map((l) => [l.consent_id, l])), [legal]);

  const errors = useMemo(() => {
    if (!submitted) return [];
    const list: Array<{ id: string; message: string }> = [];
    if (displayName.trim().length < 2) list.push({ id: 'reg-name', message: 'Укажите имя пользователя' });
    if (!email.includes('@')) list.push({ id: 'reg-email', message: 'Укажите корректный email' });
    if (password.length < 10) list.push({ id: 'reg-password', message: 'Пароль не короче 10 символов' });
    else if (!/[A-Za-zА-Яа-яЁё]/.test(password) || !/\d/.test(password)) {
      list.push({ id: 'reg-password', message: 'В пароле нужны буква и цифра' });
    }
    if (passwordConfirm !== password) list.push({ id: 'reg-password-confirm', message: 'Пароли не совпадают' });
    if (!acceptTerms) list.push({ id: 'reg-terms', message: 'Примите пользовательское соглашение' });
    if (!acceptOffer) list.push({ id: 'reg-offer', message: 'Примите оферту' });
    if (!acceptPd) list.push({ id: 'reg-pd', message: 'Дайте отдельное согласие на обычные ПД' });
    return list;
  }, [submitted, displayName, email, password, passwordConfirm, acceptTerms, acceptOffer, acceptPd]);

  function onAvatarChange(file: File | null) {
    setAvatarError(null);
    setAvatarDataUrl(null);
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setAvatarError('Допустимы JPEG, PNG или WebP');
      return;
    }
    if (file.size > 200_000) {
      setAvatarError('Файл не больше 200 КБ');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') setAvatarDataUrl(reader.result);
    };
    reader.onerror = () => setAvatarError('Не удалось прочитать файл');
    reader.readAsDataURL(file);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    setServerError(null);
    setServerMsg(null);
    const nameOk = displayName.trim().length >= 2;
    const passOk = password.length >= 10 && /[A-Za-zА-Яа-яЁё]/.test(password) && /\d/.test(password);
    if (!nameOk || !acceptTerms || !acceptOffer || !acceptPd || !passOk || !email.includes('@') || passwordConfirm !== password) {
      return;
    }

    const accepts = [];
    for (const [checked, key] of [
      [acceptTerms, 'terms_of_use'],
      [acceptOffer, 'offer'],
      [acceptPd, 'personal_data_processing'],
      [acceptMarketing, 'marketing'],
    ] as const) {
      if (!checked) continue;
      const doc = byId[key];
      if (!doc) {
        setServerError('Не загружены актуальные версии документов');
        return;
      }
      accepts.push({
        consent_id: doc.consent_id,
        consent_version: doc.consent_version,
        content_hash: doc.content_hash,
      });
    }

    const res = await fetch(`${getApiBase()}/auth/register`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        display_name: displayName.trim(),
        locale: 'ru-RU',
        accepts,
        ...(avatarDataUrl ? { avatar_data_url: avatarDataUrl } : {}),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setServerError(data?.detail?.detail || data?.detail || 'Ошибка регистрации');
      return;
    }
    setServerMsg(data.message || 'Проверьте email');
  }

  return (
    <div className="dar-content dar-auth-card dar-auth-card--wide">
      <h1 className="dar-page-title">Регистрация</h1>
      <p className="dar-page-lead">
        Обязательные согласия не отмечены заранее. Согласие на обычные ПД отдельно от соглашения и оферты.
        Медицинские данные здесь не запрашиваются.
      </p>
      <ScreenStateView
        state={state}
        ready={
          <form className="dar-stack" noValidate onSubmit={onSubmit}>
            <FormErrorSummary errors={errors} />
            {serverError ? (
              <p className="dar-field__error" role="alert">
                {serverError}
              </p>
            ) : null}
            {legalLoadError ? (
              <p className="dar-field__error" role="alert">
                {legalLoadError}
              </p>
            ) : null}
            <Input
              id="reg-name"
              label="Имя пользователя"
              type="text"
              autoComplete="username"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              hint="Этим именем вы войдёте в кабинет"
              error={errors.find((x) => x.id === 'reg-name')?.message}
            />
            <Input
              id="reg-email"
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.find((x) => x.id === 'reg-email')?.message}
            />
            <Input
              id="reg-password"
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              hint="Не короче 10 символов, буква и цифра"
              error={errors.find((x) => x.id === 'reg-password')?.message}
            />
            <Input
              id="reg-password-confirm"
              label="Повторите пароль"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              error={errors.find((x) => x.id === 'reg-password-confirm')?.message}
            />
            <div className="dar-field">
              <label className="dar-field__label" htmlFor="reg-avatar">
                Фото профиля
              </label>
              <input
                id="reg-avatar"
                className="dar-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => onAvatarChange(e.target.files?.[0] ?? null)}
              />
              <p className="dar-field__hint">Необязательно. JPEG, PNG или WebP, до 200 КБ.</p>
              {avatarError ? (
                <p className="dar-field__error" role="alert">
                  {avatarError}
                </p>
              ) : null}
              {avatarDataUrl ? <img src={avatarDataUrl} alt="" className="dar-avatar-preview" /> : null}
            </div>

            <fieldset className="dar-fieldset">
              <legend>Обязательные документы</legend>
              <p className="dar-muted">
                Политика ПД (ознакомительно):{' '}
                <a
                  href={byId.privacy_policy ? `${getApiBase()}/legal/documents/${byId.privacy_policy.id}/text` : '#'}
                  target="_blank"
                  rel="noreferrer"
                >
                  privacy_policy {byId.privacy_policy?.consent_version ?? '…'}
                </a>
              </p>
              <div className="dar-stack">
                <Checkbox
                  id="reg-terms"
                  checked={acceptTerms}
                  onChange={setAcceptTerms}
                  label={
                    <span>
                      Принимаю{' '}
                      <a
                        href={byId.terms_of_use ? `${getApiBase()}/legal/documents/${byId.terms_of_use.id}/text` : '#'}
                        target="_blank"
                        rel="noreferrer"
                      >
                        пользовательское соглашение {byId.terms_of_use?.consent_version ?? '…'}
                      </a>
                      {' '}
                      (в том числе статус формируемых документов)
                    </span>
                  }
                />
                <Checkbox
                  id="reg-offer"
                  checked={acceptOffer}
                  onChange={setAcceptOffer}
                  label={
                    <span>
                      Принимаю{' '}
                      <a
                        href={byId.offer ? `${getApiBase()}/legal/documents/${byId.offer.id}/text` : '#'}
                        target="_blank"
                        rel="noreferrer"
                      >
                        оферту {byId.offer?.consent_version ?? '…'}
                      </a>
                    </span>
                  }
                />
                <Checkbox
                  id="reg-pd"
                  checked={acceptPd}
                  onChange={setAcceptPd}
                  label={
                    <span>
                      Отдельно даю согласие на обработку{' '}
                      <a
                        href={
                          byId.personal_data_processing
                            ? `${getApiBase()}/legal/documents/${byId.personal_data_processing.id}/text`
                            : '#'
                        }
                        target="_blank"
                        rel="noreferrer"
                      >
                        обычных персональных данных {byId.personal_data_processing?.consent_version ?? '…'}
                      </a>
                    </span>
                  }
                />
              </div>
            </fieldset>

            <Checkbox
              id="reg-marketing"
              checked={acceptMarketing}
              onChange={setAcceptMarketing}
              label={
                <span>
                  Получать маркетинговые сообщения (необязательно){' '}
                  {byId.marketing ? `· ${byId.marketing.consent_version}` : ''}
                </span>
              }
            />

            <Button type="submit">Создать аккаунт</Button>
            <p>
              Уже есть аккаунт? <Link href="/auth/login">Войти</Link>
            </p>
            {serverMsg ? (
              <p role="status">
                {serverMsg} <Link href="/auth/login">Перейти ко входу</Link>
              </p>
            ) : null}
          </form>
        }
      />
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<Skeleton height={200} />}>
      <RegisterForm />
    </Suspense>
  );
}

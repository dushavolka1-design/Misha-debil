'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button, FormErrorSummary, Input, PasswordInput, Stepper } from '@dar/ui';
import { buildAccepts, emptyAccepts, parseLegalItems, requiredConsents, validateCredentials, type ConsentId, type FieldError, type LegalItem } from './authModel';

export type RegistrationPayload = { display_name: string; email: string; password: string; locale: string; accepts: ReturnType<typeof buildAccepts> };
export type AuthFlowProps = {
  mode: 'register' | 'login';
  loadLegal: (signal: AbortSignal) => Promise<unknown>;
  legalUrl: (id: string) => string;
  register: (payload: RegistrationPayload) => Promise<void>;
  login: (payload: { username: string; password: string }) => Promise<void>;
  errorMessage: (error: unknown) => string;
};
const consentText: Record<ConsentId, { id: string; lead: string; title: string }> = {
  terms_of_use: { id: 'reg-terms', lead: 'Принимаю', title: 'пользовательское соглашение' },
  offer: { id: 'reg-offer', lead: 'Принимаю', title: 'оферту' },
  personal_data_processing: { id: 'reg-pd', lead: 'Отдельно даю согласие на', title: 'обработку обычных персональных данных' },
  marketing: { id: 'reg-marketing', lead: 'Хочу получать', title: 'маркетинговые сообщения' },
};

export function AuthFlow({ mode, loadLegal, legalUrl, register, login, errorMessage }: AuthFlowProps) {
  const isRegister = mode === 'register';
  const [step, setStep] = useState(0);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accepts, setAccepts] = useState(emptyAccepts);
  const [documents, setDocuments] = useState<LegalItem[]>([]);
  const [legalStatus, setLegalStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [reload, setReload] = useState(0);
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [serverError, setServerError] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const errorBox = useRef<HTMLDivElement>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!isRegister) return;
    const controller = new AbortController();
    setLegalStatus('loading');
    setAccepts(emptyAccepts());
    void loadLegal(controller.signal).then((value) => {
      if (controller.signal.aborted) return;
      setDocuments(parseLegalItems(value));
      setLegalStatus('ready');
    }).catch(() => {
      if (controller.signal.aborted) return;
      setDocuments([]); setLegalStatus('error');
    });
    return () => controller.abort();
  }, [isRegister, loadLegal, reload]);
  useEffect(() => { if (step > 0) heading.current?.focus(); }, [step]);
  useEffect(() => { if (errors.length || serverError) errorBox.current?.focus(); }, [errors, serverError]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    setServerError('');
    const problems = isRegister ? validateCredentials({ displayName, email, password }) : [
      ...(displayName.trim().length < 2 ? [{ id: 'login-username', message: 'Укажите имя пользователя.' }] : []),
      ...(!password ? [{ id: 'login-password', message: 'Введите пароль.' }] : []),
    ];
    setErrors(problems);
    if (problems.length) { setStep(0); return; }
    if (isRegister && step === 0) { setStep(1); return; }
    if (isRegister) {
      if (legalStatus !== 'ready') { setServerError('Сначала загрузите актуальные документы.'); return; }
      const missing = requiredConsents.filter((id) => !accepts[id]).map((id) => ({ id: consentText[id].id, message: `Обязательное подтверждение: ${consentText[id].title}.` }));
      setErrors(missing);
      if (missing.length) return;
    }
    submitting.current = true; setBusy(true);
    try {
      if (isRegister) {
        await register({ display_name: displayName.trim(), email: email.trim(), password, locale: 'ru-RU', accepts: buildAccepts(documents, accepts) });
        if (mounted.current) { setPassword(''); setStep(2); }
      } else {
        await login({ username: displayName.trim(), password });
        if (mounted.current) setPassword('');
      }
    } catch (error) {
      if (mounted.current) setServerError(errorMessage(error));
    } finally {
      submitting.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const title = !isRegister ? 'С возвращением' : step === 0 ? 'Создайте свой аккаунт' : step === 1 ? 'Ваши данные — ваш выбор' : 'Проверьте почту';
  const fieldError = (id: string) => errors.find((error) => error.id === id)?.message;
  const privacy = documents.find((doc) => doc.consent_id === 'privacy_policy');
  return (
    <section className="docly-auth" aria-labelledby="auth-title" lang="ru">
      <aside className="docly-auth__intro">
        <span className="docly-auth__wordmark">Docly<span aria-hidden="true">.</span></span>
        <p className="docly-auth__eyebrow">Понятно. По шагам.</p>
        <h2>Меньше сложности.<br />Больше ясности.</h2>
        <p>Проверяйте документы, готовьте сведения и возвращайтесь к своим задачам в одном месте.</p>
        <ol className="docly-auth__principles">
          <li><span aria-hidden="true">01</span><div><strong>Знайте, что перед вами</strong><p>Черновик и официальная форма — не одно и то же.</p></div></li>
          <li><span aria-hidden="true">02</span><div><strong>Проверяйте основание</strong><p>Смотрите источник, редакцию и ограничения документа.</p></div></li>
          <li><span aria-hidden="true">03</span><div><strong>Сохраняйте контроль</strong><p>Управляйте согласиями в настройках профиля.</p></div></li>
        </ol>
        <p className="docly-auth__independent">Независимый сервис. Не государственный орган. Подготовка документа не гарантирует его принятие.</p>
      </aside>
      <div className="docly-auth__panel">
        {isRegister ? <Stepper steps={['Аккаунт', 'Согласия', 'Далее']} current={step} label="Шаги регистрации" /> : null}
        <h1 id="auth-title" ref={heading} tabIndex={-1}>{title}</h1>
        <p className="docly-auth__lead">{!isRegister ? 'Войдите, чтобы продолжить работу с документами.' : step === 0 ? 'Нужны только данные для входа. Паспорт и медицинские сведения здесь не запрашиваются.' : step === 1 ? 'Прочитайте условия и подтвердите каждый обязательный пункт отдельно.' : `Запрос обработан. Если для адреса ${email} требуется подтверждение, следуйте инструкции в письме. Доставка письма пока не подтверждена.`}</p>
        {step === 2 ? (
          <div className="docly-auth__complete">
            <p>Проверьте входящие и папку «Спам». В локальном режиме отдельное подтверждение может не требоваться.</p>
            <a className="dar-btn dar-btn--primary" href="/auth/login">Перейти ко входу</a>
            <p>После входа можно проверить документ или открыть каталог форм. Фото профиля добавляется в настройках.</p>
          </div>
        ) : (
          <form onSubmit={submit} noValidate aria-busy={busy} className="docly-auth__form">
            <div ref={errorBox} tabIndex={-1}>
              <FormErrorSummary errors={errors} />
              {serverError ? <p className="docly-auth__error" role="alert">{serverError}</p> : null}
            </div>
            {step === 0 ? <>
              <Input id={isRegister ? 'reg-name' : 'login-username'} name="username" label="Имя пользователя" autoComplete="username" value={displayName} maxLength={80} required disabled={busy} onChange={(event) => setDisplayName(event.target.value)} hint={isRegister ? 'Имя для входа. Можно не использовать настоящее имя.' : undefined} error={fieldError(isRegister ? 'reg-name' : 'login-username')} />
              {isRegister ? <Input id="reg-email" name="email" label="Email" type="email" inputMode="email" autoComplete="email" value={email} required maxLength={320} disabled={busy} onChange={(event) => setEmail(event.target.value)} error={fieldError('reg-email')} /> : null}
              <PasswordInput id={isRegister ? 'reg-password' : 'login-password'} name="password" label="Пароль" autoComplete={isRegister ? 'new-password' : 'current-password'} value={password} required disabled={busy} maxLength={isRegister ? 128 : undefined} onChange={(event) => setPassword(event.target.value)} hint={isRegister ? '10–128 символов, буква и цифра. Можно вставить пароль из менеджера паролей.' : undefined} error={fieldError(isRegister ? 'reg-password' : 'login-password')} />
            </> : <>
              <p className="docly-auth__account">{displayName} · {email}</p>
              {legalStatus === 'loading' ? <p role="status">Загружаем актуальные версии документов…</p> : null}
              {legalStatus === 'error' ? <div className="docly-auth__error" role="alert"><p>Не удалось загрузить условия. Проверьте подключение и повторите попытку. Создание аккаунта пока недоступно.</p><Button onClick={() => setReload((value) => value + 1)}>Повторить загрузку</Button></div> : null}
              {legalStatus === 'ready' ? <>
                <fieldset className="docly-auth__consents" disabled={busy}>
                  <legend>Обязательные подтверждения</legend>
                  {requiredConsents.map((id) => {
                    const item = consentText[id];
                    const doc = documents.find((candidate) => candidate.consent_id === id)!;
                    return <div className="docly-auth__consent" key={id}>
                      <label htmlFor={item.id}>
                        <input type="checkbox" id={item.id} checked={accepts[id]} required aria-invalid={Boolean(fieldError(item.id)) || undefined} aria-describedby={`${item.id}-version`} onChange={(event) => setAccepts((current) => ({ ...current, [id]: event.target.checked }))} />
                        <span>{item.lead}{' '}<a href={legalUrl(doc.id)} target="_blank" rel="noreferrer">{item.title}<span className="dar-sr-only"> (откроется в новой вкладке)</span></a></span>
                      </label>
                      <p id={`${item.id}-version`}>Обязательно · версия {doc.consent_version}</p>
                    </div>;
                  })}
                </fieldset>
                {documents.find((doc) => doc.consent_id === 'marketing') ? <div className="docly-auth__optional">
                  <label htmlFor="reg-marketing"><input id="reg-marketing" type="checkbox" checked={accepts.marketing} disabled={busy} onChange={(event) => setAccepts((current) => ({ ...current, marketing: event.target.checked }))} /><span>Получать маркетинговые сообщения — необязательно.</span></label>
                  <a href={legalUrl(documents.find((doc) => doc.consent_id === 'marketing')!.id)} target="_blank" rel="noreferrer">Условия маркетингового согласия ·{' '}{documents.find((doc) => doc.consent_id === 'marketing')!.consent_version}</a>
                  <p>Можно отказаться сейчас или отозвать согласие позже в профиле.</p>
                </div> : null}
                {privacy ? <p><a href={legalUrl(privacy.id)} target="_blank" rel="noreferrer">Политика обработки персональных данных · {privacy.consent_version}</a></p> : null}
                <p className="docly-auth__notice">Согласие на медицинские данные здесь не запрашивается. Для их обработки предусмотрен отдельный шаг.</p>
              </> : null}
            </>}
            <div className="docly-auth__actions">
              {step === 1 ? <Button variant="secondary" disabled={busy} onClick={() => { setStep(0); setErrors([]); setServerError(''); }}>Назад</Button> : null}
              <Button type="submit" loading={busy} disabled={step === 1 && legalStatus !== 'ready'}>{busy ? 'Отправляем…' : !isRegister ? 'Войти' : step === 0 ? 'Продолжить' : 'Создать аккаунт'}</Button>
            </div>
            <p className="docly-auth__switch">{isRegister ? 'Уже есть аккаунт?' : 'Нет аккаунта?'}{' '}<a href={isRegister ? '/auth/login' : '/auth/register'}>{isRegister ? 'Войти' : 'Создать аккаунт'}</a></p>
            {isRegister ? <p className="docly-auth__session-note">До отправки данные остаются только в этой вкладке. При её закрытии введённое не сохраняется.</p> : null}
          </form>
        )}
      </div>
    </section>
  );
}

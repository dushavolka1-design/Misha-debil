'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import {
  Alert,
  Button,
  Dialog,
  Drawer,
  Input,
  ScreenStateView,
  Tabs,
  parseScreenState,
} from '@dar/ui';

import { getApiBase } from '../../../lib/apiBase';

type ConsentRow = {
  consent_id: string;
  active_version: string | null;
  status: string;
  last_action_at: string | null;
  last_event_id: string | null;
  legal_document_id: string | null;
};

export default function ProfileClient() {
  const state = parseScreenState(useSearchParams().get('state'));
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [consents, setConsents] = useState<ConsentRow[]>([]);
  const [email, setEmail] = useState<string>('—');
  const [displayName, setDisplayName] = useState('');
  const [hasAvatar, setHasAvatar] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(null);
  const [clearAvatar, setClearAvatar] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function refresh() {
    const res = await fetch(`${getApiBase()}/privacy/dashboard`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    setEmail(data.email);
    setDisplayName(data.display_name || '');
    setHasAvatar(Boolean(data.has_avatar));
    setConsents(data.consents || []);
    if (data.has_avatar) {
      const av = await fetch(`${getApiBase()}/auth/me/avatar`, { credentials: 'include' });
      if (av.ok) {
        const blob = await av.blob();
        setAvatarPreview((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return URL.createObjectURL(blob);
        });
      }
    } else {
      setAvatarPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function withdraw(consentId: string) {
    const res = await fetch(`${getApiBase()}/privacy/consents/withdraw`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent_id: consentId, locale: 'ru-RU' }),
    });
    const data = await res.json().catch(() => ({}));
    setMsg(data.message || (res.ok ? 'Отозвано' : 'Ошибка'));
    await refresh();
  }

  async function requestExport() {
    await fetch(`${getApiBase()}/privacy/export-request`, {
      method: 'POST',
      credentials: 'include',
    });
    setMsg('Запрос экспорта отправлен');
    await refresh();
  }

  async function requestDelete() {
    await fetch(`${getApiBase()}/privacy/delete-request`, {
      method: 'POST',
      credentials: 'include',
    });
    setDeleteOpen(false);
    setMsg('Запрос удаления отправлен (доступно даже без re-accept новой оферты)');
    await refresh();
  }

  async function saveProfile() {
    const res = await fetch(`${getApiBase()}/auth/profile`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        display_name: displayName.trim(),
        ...(avatarDataUrl ? { avatar_data_url: avatarDataUrl } : {}),
        clear_avatar: clearAvatar,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setMsg(data?.detail?.detail || data?.detail || 'Не удалось сохранить профиль');
      return;
    }
    setAvatarDataUrl(null);
    setClearAvatar(false);
    setMsg('Профиль сохранён');
    await refresh();
  }

  function onAvatarFile(file: File | null) {
    setClearAvatar(false);
    setAvatarDataUrl(null);
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 200_000) {
      setMsg('Фото: JPEG, PNG или WebP до 200 КБ');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') setAvatarDataUrl(reader.result);
    };
    reader.readAsDataURL(file);
  }

  return (
    <div>
      <h1 className="dar-page-title">Профиль и приватность</h1>
      <p className="dar-page-lead">{displayName ? `${displayName} · ${email}` : email}</p>
      {msg ? (
        <Alert title="Статус" tone="info">
          {msg}
        </Alert>
      ) : null}
      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <Tabs
              items={[
                {
                  value: 'profile',
                  label: 'Профиль',
                  panel: (
                    <div className="dar-stack">
                      <Input
                        id="profile-name"
                        label="Имя пользователя"
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                      />
                      <div className="dar-field">
                        <span className="dar-field__label">Фото</span>
                        {avatarDataUrl || avatarPreview ? (
                          <img
                            src={avatarDataUrl || avatarPreview || ''}
                            alt=""
                            className="dar-avatar-preview"
                          />
                        ) : (
                          <p className="dar-muted">Фото не задано</p>
                        )}
                        <input
                          id="profile-avatar"
                          className="dar-input"
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={(e) => onAvatarFile(e.target.files?.[0] ?? null)}
                        />
                        {hasAvatar || avatarPreview ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setClearAvatar(true);
                              setAvatarDataUrl(null);
                              setAvatarPreview((prev) => {
                                if (prev) URL.revokeObjectURL(prev);
                                return null;
                              });
                            }}
                          >
                            Убрать фото
                          </Button>
                        ) : null}
                      </div>
                      <Button onClick={() => void saveProfile()}>Сохранить профиль</Button>
                    </div>
                  ),
                },
                {
                  value: 'privacy',
                  label: 'Согласия',
                  panel: (
                    <div className="dar-stack">
                      <Alert title="Доказуемые согласия" tone="info">
                        Можно скачать точный принятый текст по событию. Published версии
                        неизменяемы.
                      </Alert>
                      <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 8 }}>
                        {consents.map((c) => (
                          <li key={c.consent_id} className="dar-panel">
                            <strong>{c.consent_id}</strong>
                            <div
                              style={{
                                fontSize: 'var(--dar-text-sm)',
                                color: 'var(--dar-color-text-muted)',
                              }}
                            >
                              версия {c.active_version ?? '—'} · {c.status}
                              {c.last_action_at ? ` · ${c.last_action_at}` : ''}
                            </div>
                            <div className="dar-row" style={{ marginTop: 8 }}>
                              {c.legal_document_id ? (
                                <a
                                  className="dar-btn dar-btn--secondary dar-btn--sm"
                                  href={`${getApiBase()}/legal/documents/${c.legal_document_id}/text`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Текст версии
                                </a>
                              ) : null}
                              {c.last_event_id ? (
                                <a
                                  className="dar-btn dar-btn--ghost dar-btn--sm"
                                  href={`${getApiBase()}/legal/events/${c.last_event_id}/proof`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Доказательство акцепта
                                </a>
                              ) : null}
                              {c.status.startsWith('accepted') &&
                              c.consent_id !== 'terms_of_use' ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => void withdraw(c.consent_id)}
                                >
                                  Отозвать
                                </Button>
                              ) : null}
                            </div>
                          </li>
                        ))}
                      </ul>
                      <Button variant="secondary" onClick={() => setPrivacyOpen(true)}>
                        Подробнее в панели
                      </Button>
                    </div>
                  ),
                },
                {
                  value: 'sessions',
                  label: 'Сессии',
                  panel: (
                    <div className="dar-stack">
                      <Button
                        variant="secondary"
                        onClick={() =>
                          void fetch(`${getApiBase()}/auth/sessions/revoke-others`, {
                            method: 'POST',
                            credentials: 'include',
                          }).then(() => setMsg('Другие сессии отозваны'))
                        }
                      >
                        Отозвать другие сессии
                      </Button>
                    </div>
                  ),
                },
                {
                  value: 'billing',
                  label: 'Подписка',
                  panel: (
                    <div className="dar-stack">
                      <Alert title="Отмена в один поток" tone="info">
                        Отмена автопродления и история платежей — в разделе подписки. Удаление
                        способа оплаты и аккаунта не маскируются.
                      </Alert>
                      <a className="dar-btn dar-btn--secondary" href="/app/billing">
                        Открыть подписку и платежи
                      </a>
                      <p
                        style={{
                          fontSize: 'var(--dar-text-sm)',
                          color: 'var(--dar-color-text-muted)',
                        }}
                      >
                        Удаление аккаунта — вкладка «Экспорт / удаление».
                      </p>
                    </div>
                  ),
                },
                {
                  value: 'delete',
                  label: 'Экспорт / удаление',
                  panel: (
                    <div className="dar-stack">
                      <Alert title="Всегда доступно" tone="warning">
                        Экспорт и удаление аккаунта доступны даже если вы не приняли новую
                        существенную оферту.
                      </Alert>
                      <Button variant="secondary" onClick={() => void requestExport()}>
                        Запросить экспорт
                      </Button>
                      <Button variant="danger" onClick={() => setDeleteOpen(true)}>
                        Запросить удаление
                      </Button>
                    </div>
                  ),
                },
              ]}
            />
            <Dialog
              open={deleteOpen}
              title="Подтверждение удаления"
              onClose={() => setDeleteOpen(false)}
            >
              <p>Будет erasure workflow. Сессии отзовутся.</p>
              <div className="dar-row">
                <Button variant="danger" onClick={() => void requestDelete()}>
                  Подтвердить
                </Button>
                <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
                  Отмена
                </Button>
              </div>
            </Dialog>
            <Drawer
              open={privacyOpen}
              title="Политика данных"
              onClose={() => setPrivacyOpen(false)}
            >
              <p>
                ConsentEvent append-only. Медицинское согласие запрашивается только перед загрузкой
                потенциально медицинского документа.
              </p>
            </Drawer>
          </div>
        }
      />
    </div>
  );
}

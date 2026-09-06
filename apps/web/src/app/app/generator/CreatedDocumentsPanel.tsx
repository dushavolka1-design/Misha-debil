'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Alert, Badge, Button, EmptyState, Skeleton } from '@dar/ui';

import { useToast } from '../../../components/Toast';
import { ApiError, apiFetch, downloadBlob, downloadGeneratedPdf } from '../../../lib/apiClient';

type HistoryItem = {
  id: string;
  kind: 'draft' | 'generated';
  catalog_form_id?: string;
  catalog_title?: string;
  form_version?: string;
  updated_at?: string;
  created_at?: string;
  preview_ok?: boolean;
};

export default function CreatedDocumentsPanel() {
  const toast = useToast();
  const [drafts, setDrafts] = useState<HistoryItem[]>([]);
  const [generated, setGenerated] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ drafts?: HistoryItem[]; generated?: HistoryItem[] }>(
        '/forms/fill/generated',
      );
      setDrafts(Array.isArray(data.drafts) ? data.drafts : []);
      setGenerated(Array.isArray(data.generated) ? data.generated : []);
    } catch (err) {
      if (err instanceof ApiError && err.code === 'unauthorized') {
        setError('Войдите в аккаунт, чтобы видеть черновики и готовые документы.');
        setDrafts([]);
        setGenerated([]);
        return;
      }
      setError(
        err instanceof ApiError ? err.detail || err.message : 'Не удалось загрузить историю',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function removeGenerated(id: string) {
    try {
      await apiFetch(`/forms/fill/generated/${id}`, { method: 'DELETE' });
      toast.showSuccess('Документ удалён');
      void load();
    } catch (err) {
      toast.showError(err instanceof ApiError ? err.detail || err.message : 'Не удалось удалить');
    }
  }

  async function copyGenerated(id: string) {
    try {
      await apiFetch(`/forms/fill/generated/${id}/copy`, { method: 'POST' });
      toast.showSuccess('Копия создана');
      void load();
    } catch (err) {
      toast.showError(
        err instanceof ApiError ? err.detail || err.message : 'Не удалось создать копию',
      );
    }
  }

  async function downloadGenerated(id: string) {
    try {
      const { blob, filename } = await downloadGeneratedPdf(id);
      downloadBlob(blob, filename);
    } catch (err) {
      toast.showError(
        err instanceof ApiError ? err.detail || err.message : 'Не удалось скачать PDF',
      );
    }
  }

  if (loading) return <Skeleton height={240} />;

  if (error) {
    return (
      <Alert title="История недоступна" tone="warning">
        {error}
      </Alert>
    );
  }

  if (drafts.length === 0 && generated.length === 0) {
    return (
      <EmptyState
        title="Созданных документов пока нет"
        description="Заполните шаблон или пройдите мастер документов — готовые файлы появятся здесь."
        action={
          <Link href="/app/generator?tab=templates" className="dar-btn dar-btn--primary">
            Перейти к шаблонам
          </Link>
        }
      />
    );
  }

  return (
    <div className="dar-stack">
      {drafts.length > 0 ? (
        <section className="dar-stack">
          <h2 className="dar-subheading">Черновики</h2>
          {drafts.map((d) => (
            <article key={d.id} className="dar-panel dar-row dar-row--between">
              <div>
                <strong>{d.catalog_title || 'Черновик'}</strong>
                <p className="dar-doc-card__meta">
                  Обновлён {d.updated_at ? new Date(d.updated_at).toLocaleString('ru-RU') : '—'}
                </p>
              </div>
              {d.catalog_form_id ? (
                <Link
                  href={`/app/forms/${d.catalog_form_id}`}
                  className="dar-btn dar-btn--secondary dar-btn--sm"
                >
                  Продолжить
                </Link>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}
      {generated.length > 0 ? (
        <section className="dar-stack">
          <h2 className="dar-subheading">Готовые документы</h2>
          {generated.map((g) => (
            <article key={g.id} className="dar-panel dar-stack">
              <div className="dar-row dar-row--between">
                <strong>{g.catalog_title || 'Документ'}</strong>
                <Badge tone={g.preview_ok ? 'success' : 'warning'}>v{g.form_version || '?'}</Badge>
              </div>
              <p className="dar-doc-card__meta">
                Создан {g.created_at ? new Date(g.created_at).toLocaleString('ru-RU') : '—'}
              </p>
              <div className="dar-row">
                <Button onClick={() => void downloadGenerated(g.id)}>Скачать</Button>
                <Button variant="secondary" size="sm" onClick={() => void copyGenerated(g.id)}>
                  Создать копию
                </Button>
                <Button variant="ghost" size="sm" onClick={() => void removeGenerated(g.id)}>
                  Удалить
                </Button>
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}

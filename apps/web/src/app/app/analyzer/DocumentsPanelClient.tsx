'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge, Button, Input, Skeleton } from '@dar/ui';

import { DeleteDocumentDialog } from '../../../components/DeleteDocumentDialog';
import { ServiceUnavailable } from '../../../components/ServiceUnavailable';
import {
  ApiError,
  fetchDocuments,
  retryAnalysis,
  startAnalysis,
  type DocumentListItem,
} from '../../../lib/apiClient';
import { formatDocumentState } from '../../../lib/statusLabels';

type Props = {
  onOpenDocument: (documentId: string, runId?: string | null) => void;
  onCompare: (documentIds: string[]) => void;
};

export default function DocumentsPanelClient({ onOpenDocument, onCompare }: Props) {
  const [items, setItems] = useState<DocumentListItem[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentListItem | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await fetchDocuments();
      setItems(docs);
    } catch (err) {
      setItems(null);
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((doc) => {
      if (search && !doc.display_name.toLowerCase().includes(search.toLowerCase())) return false;
      if (stateFilter && doc.state.toLowerCase() !== stateFilter.toLowerCase()) return false;
      if (typeFilter && (doc.detected_type ?? '').toLowerCase() !== typeFilter.toLowerCase())
        return false;
      if (dateFilter) {
        const day = doc.updated_at.slice(0, 10);
        if (day !== dateFilter) return false;
      }
      return true;
    });
  }, [items, search, stateFilter, typeFilter, dateFilter]);

  const types = useMemo(() => {
    const set = new Set<string>();
    items?.forEach((d) => {
      if (d.detected_type) set.add(d.detected_type);
    });
    return [...set].sort();
  }, [items]);

  async function onRetry(doc: DocumentListItem) {
    if (!doc.latest_run_id) return;
    setBusyId(doc.id);
    setActionError(null);
    try {
      await retryAnalysis(doc.latest_run_id);
      void load();
    } catch (err) {
      setActionError(
        err instanceof ApiError ? (err.detail ?? err.message) : 'Не удалось повторить анализ',
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onStart(doc: DocumentListItem) {
    setBusyId(doc.id);
    setActionError(null);
    try {
      const res = await startAnalysis(doc.id);
      onOpenDocument(doc.id, res.run_id);
    } catch (err) {
      setActionError(
        err instanceof ApiError ? (err.detail ?? err.message) : 'Не удалось запустить анализ',
      );
    } finally {
      setBusyId(null);
    }
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (loading) return <Skeleton height={240} label="Загрузка документов" />;

  if (error?.isConnectionError) return <ServiceUnavailable onRetry={load} />;

  if (error) {
    return (
      <div className="dar-panel" role="alert">
        <p>{error.detail ?? error.message}</p>
        <button type="button" className="dar-btn dar-btn--secondary" onClick={() => void load()}>
          Повторить
        </button>
      </div>
    );
  }

  if (!items?.length) {
    return (
      <div className="dar-empty" role="status">
        <h2 className="dar-empty__title">Документов пока нет</h2>
        <p className="dar-empty__text">Загрузите первый файл во вкладке «Новый анализ».</p>
        <Link href="/app/analyzer?tab=new" className="dar-btn dar-btn--primary">
          Новый анализ
        </Link>
      </div>
    );
  }

  return (
    <div className="dar-stack">
      <div className="dar-panel dar-stack">
        <Input
          id="doc-search"
          label="Поиск"
          placeholder="Имя файла…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="dar-filter-row">
          <label className="dar-field">
            <span className="dar-field__label">Статус</span>
            <select
              className="dar-input"
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
            >
              <option value="">Все</option>
              <option value="READY">Готов</option>
              <option value="PROCESSING">В обработке</option>
              <option value="QUARANTINED">На проверке</option>
              <option value="FAILED">Ошибка</option>
            </select>
          </label>
          {types.length > 0 ? (
            <label className="dar-field">
              <span className="dar-field__label">Тип</span>
              <select
                className="dar-input"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">Все</option>
                {types.map((t) => (
                  <option key={t} value={t}>
                    {t.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className="dar-field">
            <span className="dar-field__label">Дата обновления</span>
            <input
              className="dar-input"
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
            />
          </label>
        </div>
        {selected.size >= 2 ? (
          <Button variant="secondary" size="sm" onClick={() => onCompare([...selected])}>
            Сравнить выбранные ({selected.size})
          </Button>
        ) : null}
      </div>

      {actionError ? (
        <div className="dar-panel" role="alert">
          {actionError}
        </div>
      ) : null}

      {!filtered.length ? (
        <p role="status">Ничего не найдено по фильтрам.</p>
      ) : (
        <ul className="dar-doc-grid">
          {filtered.map((doc) => (
            <li key={doc.id} className="dar-panel dar-doc-card">
              <div className="dar-row dar-row--between">
                <label className="dar-check">
                  <input
                    type="checkbox"
                    checked={selected.has(doc.id)}
                    onChange={() => toggleSelect(doc.id)}
                  />
                  <strong>{doc.display_name}</strong>
                </label>
                <Badge>{formatDocumentState(doc.state)}</Badge>
              </div>
              <p className="dar-doc-card__meta">
                {doc.detected_type ?? 'тип не определён'} · обновлён{' '}
                {new Date(doc.updated_at).toLocaleString('ru-RU')}
              </p>
              <div className="dar-row">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onOpenDocument(doc.id, doc.latest_run_id)}
                >
                  Открыть
                </Button>
                {doc.latest_run_status === 'failed' ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busyId === doc.id}
                    onClick={() => void onRetry(doc)}
                  >
                    Повторить
                  </Button>
                ) : doc.state === 'READY' && !doc.latest_run_id ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busyId === doc.id}
                    onClick={() => void onStart(doc)}
                  >
                    Анализ
                  </Button>
                ) : null}
                <Button variant="ghost" size="sm" onClick={() => onCompare([doc.id])}>
                  Сравнить
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(doc)}>
                  Удалить
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {deleteTarget ? (
        <DeleteDocumentDialog
          documentId={deleteTarget.id}
          displayName={deleteTarget.display_name}
          open={Boolean(deleteTarget)}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => {
            setDeleteTarget(null);
            void load();
          }}
        />
      ) : null}
    </div>
  );
}

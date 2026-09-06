'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge, Button, Skeleton } from '@dar/ui';

import { ServiceUnavailable } from '../../../components/ServiceUnavailable';
import {
  ApiError,
  compareDocuments,
  fetchDocuments,
  type CompareDiffItem,
  type CompareResult,
} from '../../../lib/apiClient';
import { formatChangeType } from '../../../lib/statusLabels';

type Props = {
  presetIds?: string[];
  onOpenDocument?: (documentId: string, runId?: string | null) => void;
};

function DiffList({ title, items }: { title: string; items: CompareDiffItem[] }) {
  if (!items.length) return null;
  return (
    <section className="dar-panel dar-stack">
      <h3 className="dar-subheading" style={{ margin: 0 }}>
        {title}
      </h3>
      <ul style={{ margin: 0, paddingLeft: 20 }}>
        {items.map((item) => (
          <li key={`${item.path}-${item.change}`} style={{ marginBottom: 12 }}>
            <Badge tone={item.change === 'changed' ? 'warning' : 'info'}>
              {formatChangeType(item.change)}
            </Badge>{' '}
            <strong>{item.path}</strong>
            {item.left_text || item.right_text ? (
              <div style={{ fontSize: 'var(--dar-text-sm)', marginTop: 4 }}>
                {item.left_text ? <div>Было: {item.left_text}</div> : null}
                {item.right_text ? <div>Стало: {item.right_text}</div> : null}
              </div>
            ) : null}
            {(item.left_citation || item.right_citation) && (
              <div
                style={{
                  fontSize: 'var(--dar-text-sm)',
                  color: 'var(--dar-color-text-muted)',
                  marginTop: 4,
                }}
              >
                {item.left_citation?.quote ? (
                  <div>Цитата A: «{item.left_citation.quote.slice(0, 120)}»</div>
                ) : null}
                {item.right_citation?.quote ? (
                  <div>Цитата B: «{item.right_citation.quote.slice(0, 120)}»</div>
                ) : null}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function ComparePanelClient({ presetIds = [], onOpenDocument }: Props) {
  const [docs, setDocs] = useState<Array<{
    id: string;
    display_name: string;
    detected_type: string | null;
    state: string;
    latest_run_status: string | null;
  }> | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set(presetIds));
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchDocuments();
      setDocs(items.filter((d) => d.state === 'READY' && d.latest_run_status === 'ready'));
    } catch (err) {
      setDocs(null);
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (presetIds.length) setSelected(new Set(presetIds));
  }, [presetIds]);

  const readyDocs = useMemo(() => docs ?? [], [docs]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setResult(null);
  }

  async function runCompare() {
    const ids = [...selected];
    if (ids.length < 2) {
      setActionError('Выберите минимум два документа с готовым анализом');
      return;
    }
    setComparing(true);
    setActionError(null);
    try {
      const res = await compareDocuments(ids.slice(0, 2));
      setResult(res);
    } catch (err) {
      setResult(null);
      setActionError(err instanceof ApiError ? (err.detail ?? err.message) : 'Ошибка сравнения');
    } finally {
      setComparing(false);
    }
  }

  if (loading) return <Skeleton height={200} />;

  if (error?.isConnectionError) return <ServiceUnavailable onRetry={load} />;

  if (!readyDocs.length) {
    return (
      <div className="dar-empty" role="status">
        <h2 className="dar-subheading" style={{ margin: 0 }}>
          Недостаточно документов
        </h2>
        <p style={{ margin: 0, color: 'var(--dar-color-text-secondary)' }}>
          Нужно минимум два документа в статусе «Готов» с завершённым анализом.
        </p>
      </div>
    );
  }

  return (
    <div className="dar-split">
      <div className="dar-panel dar-stack">
        <h2 className="dar-subheading" style={{ margin: 0 }}>
          Выберите документы
        </h2>
        {readyDocs.length < 2 ? (
          <p className="dar-muted" role="status">
            Выберите второй документ с готовым разбором, чтобы сравнить.
          </p>
        ) : null}
        {readyDocs.map((d) => (
          <label key={d.id} className="dar-check">
            <input type="checkbox" checked={selected.has(d.id)} onChange={() => toggle(d.id)} />
            <span>
              {d.display_name} {d.detected_type ? <Badge>{d.detected_type}</Badge> : null}
            </span>
          </label>
        ))}
        <Button disabled={comparing || selected.size < 2} onClick={() => void runCompare()}>
          {comparing ? 'Сравнение…' : 'Сравнить'}
        </Button>
        {actionError ? (
          <p role="alert" style={{ color: 'var(--dar-color-danger)' }}>
            {actionError}
            <Button variant="ghost" size="sm" onClick={() => void runCompare()}>
              Повторить
            </Button>
          </p>
        ) : null}
      </div>

      <div className="dar-stack">
        {result?.refused ? (
          <div className="dar-panel" role="alert">
            Сравнение отклонено: {result.refusal_reason}
          </div>
        ) : result ? (
          <>
            <div className="dar-panel">
              <p style={{ margin: 0 }}>
                Сравнение документов{' '}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onOpenDocument?.(result.left_document_id)}
                >
                  {result.left_document_id.slice(0, 8)}…
                </Button>{' '}
                и{' '}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onOpenDocument?.(result.right_document_id)}
                >
                  {result.right_document_id.slice(0, 8)}…
                </Button>
              </p>
            </div>
            <DiffList title="Стороны" items={result.party_diffs} />
            <DiffList title="Разделы" items={result.section_diffs} />
            <DiffList title="Пункты" items={result.clause_diffs} />
            {!result.party_diffs.length &&
            !result.section_diffs.length &&
            !result.clause_diffs.length ? (
              <p role="status">Различий по извлечённым фактам не найдено.</p>
            ) : null}
          </>
        ) : (
          <div className="dar-panel">
            <p style={{ margin: 0, color: 'var(--dar-color-text-secondary)' }}>
              Выберите два документа и нажмите «Сравнить». Данные загружаются с сервера по вашим
              document ID.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

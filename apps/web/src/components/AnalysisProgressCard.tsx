'use client';

import { useCallback, useEffect, useState } from 'react';

import { Progress, Skeleton } from '@dar/ui';

import { ServiceUnavailable } from './ServiceUnavailable';
import { ApiError, fetchAnalysisProgress, fetchAnalysisRun } from '../lib/apiClient';
import { formatDocumentState, formatStage } from '../lib/statusLabels';

type ProgressItem = { stage: string; percent: number; page?: number | null; error_code?: string | null };

type Props = {
  runId: string;
  onReady?: (documentId: string, runId: string) => void;
  compact?: boolean;
};

export function AnalysisProgressCard({ runId, onReady, compact = false }: Props) {
  const [progress, setProgress] = useState<ProgressItem[]>([]);
  const [status, setStatus] = useState<string>('queued');
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [run, events] = await Promise.all([fetchAnalysisRun(runId), fetchAnalysisProgress(runId)]);
      setStatus(run.status);
      setDocumentId(run.document_id);
      setProgress(events);
      if (run.status === 'ready' && onReady) {
        onReady(run.document_id, runId);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки прогресса'));
    } finally {
      setLoading(false);
    }
  }, [runId, onReady]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (status !== 'ready' && status !== 'failed') void load();
    }, 3500);
    return () => clearInterval(timer);
  }, [load, status]);

  if (loading && !progress.length) {
    return <Skeleton height={compact ? 120 : 180} label="Загрузка прогресса" />;
  }

  if (error?.isConnectionError) {
    return <ServiceUnavailable onRetry={load} />;
  }

  if (error) {
    return (
      <div className="dar-panel" role="alert">
        <p>{error.detail ?? error.message}</p>
        <button type="button" className="dar-btn dar-btn--secondary dar-btn--sm" onClick={() => void load()}>
          Повторить
        </button>
      </div>
    );
  }

  const pct = progress.length ? progress[progress.length - 1]!.percent : 0;
  const stage = progress.length ? formatStage(progress[progress.length - 1]!.stage) : formatDocumentState(status);

  return (
    <div className="dar-panel dar-stack" role="status" aria-live="polite">
      <Progress value={pct} label={stage} />
      <p className="dar-muted">
        Статус: {formatDocumentState(status)}
        {documentId ? (
          <>
            {' '}
            · документ <span className="dar-mono">{documentId.slice(0, 8)}</span>
          </>
        ) : null}
      </p>
      {!compact && progress.length ? (
        <ol className="dar-timeline" aria-label="Ход анализа">
          {progress.slice(-6).map((ev, idx) => (
            <li key={`${ev.stage}-${idx}`} className="dar-timeline__item">
              <span className="dar-timeline__dot" aria-hidden="true" />
              <div>
                <strong>{formatStage(ev.stage)}</strong>
                {ev.error_code ? <span className="dar-status-text--danger"> · {ev.error_code}</span> : null}
                <div className="dar-timeline__time">{ev.percent}%</div>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

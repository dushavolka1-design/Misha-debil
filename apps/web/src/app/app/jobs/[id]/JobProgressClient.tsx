'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Progress, Skeleton } from '@dar/ui';

import { ServiceUnavailable } from '../../../../components/ServiceUnavailable';
import { ApiError, fetchAnalysisProgress, fetchAnalysisRun } from '../../../../lib/apiClient';
import { formatStatus } from '../../../../lib/statusLabels';

type ProgressItem = {
  stage: string;
  percent: number;
  page?: number | null;
  error_code?: string | null;
};

export default function JobProgressClient({ runId }: { runId: string }) {
  const [title, setTitle] = useState<string>('Анализ документа');
  const [progress, setProgress] = useState<ProgressItem[]>([]);
  const [status, setStatus] = useState<string>('queued');
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [run, events] = await Promise.all([
        fetchAnalysisRun(runId) as Promise<{ status: string; document_id: string }>,
        fetchAnalysisProgress(runId) as Promise<ProgressItem[]>,
      ]);
      setStatus(run.status);
      setProgress(events);
      setTitle(`Анализ · документ ${run.document_id.slice(0, 8)}…`);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки'));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (status !== 'ready' && status !== 'failed') void load();
    }, 4000);
    return () => clearInterval(timer);
  }, [load, status]);

  if (loading && !progress.length) {
    return <Skeleton height={200} />;
  }

  if (error?.isConnectionError) {
    return <ServiceUnavailable onRetry={load} />;
  }

  const pct = progress.length ? progress[progress.length - 1]!.percent : 0;
  const stage = progress.length ? progress[progress.length - 1]!.stage : formatStatus(status);

  return (
    <div className="dar-stack">
      <div className="dar-panel">
        <Progress value={pct} label={stage} />
        <p style={{ margin: '8px 0 0', color: 'var(--dar-color-text-secondary)' }}>
          Статус: {formatStatus(status)}
        </p>
      </div>
      <ul className="dar-steps" style={{ listStyle: 'none', padding: 0 }}>
        {progress.map((ev, idx) => (
          <li key={`${ev.stage}-${idx}`} className="dar-step">
            <span className="dar-step__num" aria-hidden="true">
              {ev.percent}
            </span>
            <div>
              <strong>{ev.stage}</strong>
            </div>
          </li>
        ))}
      </ul>
      {status === 'ready' ? (
        <Link className="dar-btn dar-btn--primary" href={`/app/reports/${runId}`}>
          Открыть отчёт
        </Link>
      ) : null}
    </div>
  );
}

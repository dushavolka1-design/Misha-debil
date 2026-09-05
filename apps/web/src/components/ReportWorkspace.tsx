'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';

import {
  Badge,
  ConfidenceIndicator,
  DocumentViewer,
  FindingCard,
  Skeleton,
  SourceCitation,
} from '@dar/ui';

import { ServiceUnavailable } from './ServiceUnavailable';
import { ApiError, fetchAnalysisRun } from '../lib/apiClient';
import { formatUncertainty } from '../lib/statusLabels';

type RunPayload = {
  id: string;
  status: string;
  findings: Array<{
    id: string;
    kind: string;
    entity_type: string;
    raw_text: string;
    normalized_value: unknown;
    confidence: number;
    uncertainty_state: string;
    citation: { page?: number; quote?: string; bbox?: { x: number; y: number; w: number; h: number } };
  }>;
  pages: Array<{
    page_number: number;
    width: number;
    height: number;
    rotation: number;
    confidence: number;
    language: string;
    source: string;
    error_code: string | null;
    layout_region_types: string[];
  }>;
};

export function ReportWorkspace() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [run, setRun] = useState<RunPayload | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string>('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await fetchAnalysisRun(runId)) as RunPayload;
      setRun(data);
      if (data.findings[0]) setActiveId(data.findings[0].id);
    } catch (err) {
      setRun(null);
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки отчёта'));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const active = useMemo(
    () => run?.findings.find((f) => f.id === activeId) ?? run?.findings[0],
    [run, activeId],
  );

  const page = useMemo(() => {
    if (!run || !active?.citation?.page) return run?.pages[0];
    return run.pages.find((p) => p.page_number === active.citation.page) ?? run.pages[0];
  }, [run, active]);

  if (loading) {
    return <Skeleton height={320} label="Загрузка отчёта" />;
  }

  if (error?.isConnectionError) {
    return <ServiceUnavailable onRetry={load} />;
  }

  if (error || !run) {
    return (
      <div className="dar-panel" role="alert">
        <p>{error?.message ?? 'Отчёт недоступен'}</p>
        <button type="button" className="dar-btn dar-btn--secondary" onClick={() => void load()}>
          Повторить
        </button>
      </div>
    );
  }

  if (run.status !== 'ready') {
    return (
      <div className="dar-panel">
        <p>Анализ ещё выполняется (статус: {run.status}).</p>
        <Link href={`/app/jobs/${runId}`} className="dar-btn dar-btn--secondary">
          Открыть прогресс
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link href="/app/analyzer?tab=documents" className="dar-back-link">
        ← Мои документы
      </Link>
      <h1 className="dar-page-title">Отчёт</h1>
      <p className="dar-page-lead">Нажмите на пункт — справа подсветка фрагмента в документе.</p>

      <div className="dar-stack">
        <div className="dar-row">
          <Badge tone="info">Результаты модели</Badge>
          <Link href="/app/analyzer?tab=compare" className="dar-btn dar-btn--ghost">
            К сравнению
          </Link>
        </div>

        <div className="dar-workspace">
          <div className="dar-stack">
            <section className="dar-card" aria-labelledby="findings-sec">
              <h2 id="findings-sec" className="dar-subheading">
                Результаты
              </h2>
              <div className="dar-stack">
                {run.findings.map((finding) => (
                  <div key={finding.id} className="dar-stack">
                    <FindingCard
                      title={finding.entity_type}
                      kind={finding.kind as 'fact' | 'inference'}
                      value={String(finding.normalized_value ?? finding.raw_text)}
                      uncertainty={formatUncertainty(finding.uncertainty_state)}
                      active={finding.id === active?.id}
                      onSelect={() => setActiveId(finding.id)}
                    />
                    <ConfidenceIndicator value={finding.confidence} />
                  </div>
                ))}
              </div>
            </section>
          </div>

          <DocumentViewer
            pageLabel={`Страница ${page?.page_number ?? 1} / ${run.pages.length || 1}`}
            quote={active?.citation?.quote ? active.citation.quote.slice(0, 48) : 'Фрагмент'}
            highlight={
              active?.citation?.bbox && page
                ? {
                    left: `${(active.citation.bbox.x / page.width) * 100}%`,
                    top: `${(active.citation.bbox.y / page.height) * 100}%`,
                    width: `${(active.citation.bbox.w / page.width) * 100}%`,
                    height: `${(active.citation.bbox.h / page.height) * 100}%`,
                  }
                : null
            }
          >
            <p className="dar-doc-line">{active?.citation?.quote ?? 'Текст фрагмента недоступен в предпросмотре.'}</p>
          </DocumentViewer>
        </div>
        {active?.citation?.quote ? (
          <SourceCitation title="Цитата из документа" version="1" snapshotId={run.id.slice(0, 8)} />
        ) : null}
      </div>
    </div>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  Badge,
  Button,
  ConfidenceIndicator,
  DocumentViewer,
  FindingCard,
  Skeleton,
} from '@dar/ui';

import { AnalysisProgressCard } from '../../../components/AnalysisProgressCard';
import { DeleteDocumentDialog } from '../../../components/DeleteDocumentDialog';
import { ExportDisclaimerDialog } from '../../../components/ExportDisclaimerDialog';
import { ServiceUnavailable } from '../../../components/ServiceUnavailable';
import { useToast } from '../../../components/Toast';
import {
  ApiError,
  type AnalysisFinding,
  type AnalysisRun,
  type DocumentDetail,
  downloadBlob,
  downloadDocumentDerived,
  exportAnalysisRun,
  fetchAnalysisRun,
  fetchDocument,
  fetchDocumentRuns,
  retryAnalysis,
  startAnalysis,
  submitFeedback,
  type FeedbackKind,
} from '../../../lib/apiClient';
import {
  formatDocumentState,
  formatEntityType,
  formatFindingKind,
  formatSeverity,
  formatUncertainty,
} from '../../../lib/statusLabels';

type Props = {
  documentId: string;
  runId?: string | null;
  onBack: () => void;
  onCompare?: (documentId: string) => void;
};

type DetailTab = 'main' | 'risks' | 'conflicts' | 'details' | 'source';

const DETAIL_TABS: Array<{ value: DetailTab; label: string }> = [
  { value: 'main', label: 'Основное' },
  { value: 'risks', label: 'Риски' },
  { value: 'conflicts', label: 'Противоречия' },
  { value: 'details', label: 'Реквизиты и сроки' },
  { value: 'source', label: 'Исходник' },
];

const REQUISITE_PREFIXES = ['party.', 'amount.', 'doc.date', 'party.identifier'];

function isRequisite(entityType: string): boolean {
  return REQUISITE_PREFIXES.some((p) => entityType.startsWith(p) || entityType === p);
}

function FindingFeedbackRow({ targetId, targetType }: { targetId: string; targetType: 'finding' | 'rule_hit' }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function send(kind: FeedbackKind) {
    setErr(null);
    setMsg(null);
    try {
      const res = await submitFeedback({ target_type: targetType, target_id: targetId, kind });
      setMsg(res.message);
    } catch (e) {
      setErr(e instanceof ApiError ? (e.detail ?? e.message) : 'Ошибка сохранения');
    }
  }

  return (
    <div className="dar-feedback-row">
      <Button variant="ghost" onClick={() => void send('useful')}>
        Полезно
      </Button>
      <Button variant="ghost" onClick={() => void send('error')}>
        Ошибка
      </Button>
      <Button variant="ghost" onClick={() => void send('bad_citation')}>
        Неверная цитата
      </Button>
      {msg ? (
        <span className="dar-status-text--success" role="status">
          {msg}
        </span>
      ) : null}
      {err ? (
        <span className="dar-status-text--danger" role="alert">
          {err}
        </span>
      ) : null}
    </div>
  );
}

function CitationPreview({
  finding,
  page,
}: {
  finding: AnalysisFinding | null;
  page: AnalysisRun['pages'][0] | undefined;
}) {
  if (!finding?.citation) {
    return (
      <DocumentViewer pageLabel="Страница">
        <p className="dar-doc-line">Выберите пункт слева для подсветки цитаты.</p>
      </DocumentViewer>
    );
  }
  const highlight =
    finding.citation.bbox && page
      ? {
          left: `${(finding.citation.bbox.x / page.width) * 100}%`,
          top: `${(finding.citation.bbox.y / page.height) * 100}%`,
          width: `${(finding.citation.bbox.w / page.width) * 100}%`,
          height: `${(finding.citation.bbox.h / page.height) * 100}%`,
        }
      : null;
  return (
    <DocumentViewer pageLabel={`Страница ${page?.page_number ?? 1}`} quote={finding.citation.quote?.slice(0, 72)} highlight={highlight}>
      <p className="dar-doc-line">{finding.citation.quote || finding.raw_text}</p>
    </DocumentViewer>
  );
}

export default function DocumentDetailView({ documentId, runId: initialRunIdProp, onBack, onCompare }: Props) {
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [runId, setRunId] = useState<string | null>(initialRunIdProp ?? null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [activeFindingId, setActiveFindingId] = useState<string>('');
  const [minConfidence, setMinConfidence] = useState(0);
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'high' | 'medium'>('all');
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);
  const [exportDialog, setExportDialog] = useState<'pdf' | 'json' | null>(null);
  const toast = useToast();
  const [tab, setTab] = useState<DetailTab>('main');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let resolvedDocId = documentId;
      if (!resolvedDocId && (initialRunIdProp ?? runId)) {
        const rid = initialRunIdProp ?? runId!;
        const runPeek = await fetchAnalysisRun(rid);
        resolvedDocId = runPeek.document_id;
      }
      if (!resolvedDocId) {
        throw new ApiError('http', 'Не указан документ');
      }
      const document = await fetchDocument(resolvedDocId);
      setDoc(document);
      let activeRunId = initialRunIdProp ?? runId;
      if (!activeRunId) {
        const runs = await fetchDocumentRuns(resolvedDocId);
        const ready = [...runs].reverse().find((r) => r.status === 'ready');
        activeRunId = ready?.run_id ?? runs[runs.length - 1]?.run_id ?? null;
      }
      if (activeRunId) {
        setRunId(activeRunId);
        const runData = await fetchAnalysisRun(activeRunId);
        setRun(runData);
        const firstVisible = runData.findings.find((f) => f.entity_type !== 'analysis.capability');
        if (firstVisible) setActiveFindingId(firstVisible.id);
      } else {
        setRun(null);
      }
    } catch (err) {
      setDoc(null);
      setRun(null);
      setError(err instanceof ApiError ? err : new ApiError('network', 'Ошибка загрузки'));
    } finally {
      setLoading(false);
    }
  }, [documentId, initialRunIdProp, runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const activeFinding = useMemo(
    () => run?.findings.find((f) => f.id === activeFindingId) ?? run?.findings[0],
    [run, activeFindingId],
  );

  const activePage = useMemo(() => {
    if (!run || !activeFinding?.citation?.page) return run?.pages[0];
    return run.pages.find((p) => p.page_number === activeFinding.citation.page) ?? run.pages[0];
  }, [run, activeFinding]);

  const filteredFindings = useMemo(() => {
    if (!run) return [];
    return run.findings.filter((f) => {
      if (f.entity_type === 'analysis.capability') return false;
      if (f.confidence < minConfidence / 100) return false;
      if (priorityFilter === 'high' && f.confidence < 0.75) return false;
      if (priorityFilter === 'medium' && (f.confidence < 0.5 || f.confidence >= 0.9)) return false;
      if (tab === 'details') return isRequisite(f.entity_type);
      if (tab === 'main') return !isRequisite(f.entity_type);
      return true;
    });
  }, [run, minConfidence, priorityFilter, tab]);

  const riskHits = useMemo(() => {
    if (!run) return [];
    return run.rule_hits.filter(
      (h) => h.severity === 'high' || h.severity === 'medium' || h.result_kind === 'review_question',
    );
  }, [run]);

  const conflictHits = useMemo(() => {
    if (!run) return [];
    return run.rule_hits.filter((h) => h.result_kind === 'structural_conflict');
  }, [run]);

  async function onRetry() {
    if (!runId) return;
    try {
      await retryAnalysis(runId);
      void load();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError('http', 'Не удалось повторить анализ'));
    }
  }

  async function onRestart() {
    try {
      const res = await startAnalysis(documentId);
      setRunId(res.run_id);
      void load();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError('http', 'Не удалось запустить анализ'));
    }
  }

  async function onExport(format: 'pdf' | 'json') {
    if (!runId) return;
    setExportErr(null);
    try {
      const blob = await exportAnalysisRun(runId, format);
      downloadBlob(blob, `report-${runId.slice(0, 8)}.${format}`);
      toast.showSuccess(`Файл ${format.toUpperCase()} сохранён`);
      setExportDialog(null);
    } catch (e) {
      setExportErr(e instanceof ApiError ? (e.detail ?? e.message) : 'Ошибка экспорта');
    }
  }

  if (loading) return <Skeleton height={360} label="Загрузка документа" />;

  if (error?.isConnectionError) return <ServiceUnavailable onRetry={load} />;

  if (error || !doc) {
    return (
      <div className="dar-panel" role="alert">
        <p>{error?.detail ?? error?.message ?? 'Документ недоступен'}</p>
        <button type="button" className="dar-btn dar-btn--secondary" onClick={() => void load()}>
          Повторить
        </button>
      </div>
    );
  }

  const showSplit = tab === 'main' || tab === 'details';
  const advancedUnavailable = run?.status === 'ready' && run.llm_available !== true;
  const localFactCount = run?.findings.filter((f) => f.entity_type !== 'analysis.capability').length ?? 0;

  return (
    <div className="dar-stack">
      <button type="button" className="dar-back-link" onClick={onBack}>
        ← Мои документы
      </button>

      <header className="dar-panel dar-panel--hero dar-stack">
        <div className="dar-row dar-row--between">
          <div>
            <h2 className="dar-subheading">{doc.display_name}</h2>
            <p className="dar-doc-card__meta">
              Загружен {new Date(doc.created_at).toLocaleString('ru-RU')}
              {doc.detected_type ? ` · ${doc.detected_type.toUpperCase()}` : ''}
            </p>
          </div>
          <Badge tone={doc.state === 'READY' ? 'success' : 'warning'}>{formatDocumentState(doc.state)}</Badge>
        </div>
        <div className="dar-row">
          {run?.status === 'ready' ? (
            <>
              <Button variant="secondary" size="sm" onClick={() => setExportDialog('pdf')}>
                Экспорт PDF
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setExportDialog('json')}>
                Экспорт JSON
              </Button>
            </>
          ) : null}
          {run?.status === 'failed' ? (
            <Button variant="secondary" size="sm" onClick={() => void onRetry()}>
              Повторить анализ
            </Button>
          ) : null}
          {doc.state === 'READY' && !run ? (
            <Button variant="primary" size="sm" onClick={() => void onRestart()}>
              Запустить анализ
            </Button>
          ) : null}
          {onCompare ? (
            <Button variant="ghost" size="sm" onClick={() => onCompare(documentId)}>
              Сравнить
            </Button>
          ) : null}
          <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
            Удалить
          </Button>
        </div>
        {exportErr ? (
          <p className="dar-status-text--danger" role="alert">
            {exportErr}
          </p>
        ) : null}
      </header>

      <ExportDisclaimerDialog
        open={exportDialog !== null}
        formatLabel={exportDialog === 'json' ? 'JSON' : 'PDF'}
        onClose={() => setExportDialog(null)}
        onConfirm={() => {
          if (exportDialog) void onExport(exportDialog);
        }}
      />

      {run && run.status !== 'ready' && run.status !== 'failed' && runId ? (
        <AnalysisProgressCard runId={runId} compact />
      ) : null}

      {run?.status === 'ready' ? (
        <>
          <div className="dar-metrics" aria-label="Метрики результата">
            <div className="dar-metric">
              <span className="dar-metric__value">{localFactCount}</span>
              <span className="dar-metric__label">Локальные факты</span>
            </div>
            <div className="dar-metric">
              <span className="dar-metric__value">{riskHits.length}</span>
              <span className="dar-metric__label">Риски</span>
            </div>
            <div className="dar-metric">
              <span className="dar-metric__value">{run.pages.length}</span>
              <span className="dar-metric__label">Страницы</span>
            </div>
          </div>

          {advancedUnavailable ? (
            <div className="dar-callout dar-callout--warning" role="status">
              <p>
                <strong>Локально выполнено:</strong>{' '}
                {(run.local_steps && run.local_steps.length
                  ? run.local_steps
                  : ['Распознавание текста', 'Извлечение фактов', 'Проверка правил']
                ).join(', ')}
                .
              </p>
              <p>
                Файл разобран на этом компьютере. Расширенная модель не подключена — ниже только
                извлечённые факты и правила.
              </p>
            </div>
          ) : null}

          <div className="dar-panel dar-panel--inset dar-filter-row">
            <label className="dar-field">
              <span className="dar-field__label">Мин. уверенность, %</span>
              <input
                className="dar-input"
                type="range"
                min={0}
                max={95}
                step={5}
                value={minConfidence}
                onChange={(e) => setMinConfidence(Number(e.target.value))}
              />
              <span>{minConfidence}%</span>
            </label>
            <label className="dar-field">
              <span className="dar-field__label">Приоритет</span>
              <select
                className="dar-input"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as typeof priorityFilter)}
              >
                <option value="all">Все</option>
                <option value="high">Высокая уверенность</option>
                <option value="medium">Средняя</option>
              </select>
            </label>
          </div>

          <div className="dar-tabs" role="tablist" aria-label="Разделы документа">
            {DETAIL_TABS.map((t) => (
              <button
                key={t.value}
                type="button"
                className="dar-tabs__tab"
                role="tab"
                aria-selected={tab === t.value}
                onClick={() => setTab(t.value)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'source' ? (
            <section className="dar-panel dar-stack">
              <p>Страниц в документе: {run.pages.length}</p>
              <ul>
                {run.pages.map((p) => (
                  <li key={p.page_number}>
                    Стр. {p.page_number}: {p.source}, уверенность {(p.confidence * 100).toFixed(0)}%
                    {p.error_code ? ` · ${p.error_code}` : ''}
                  </li>
                ))}
              </ul>
              {run.findings
                .filter((f) => f.entity_type === 'doc.excerpt' || f.citation?.quote)
                .slice(0, 8)
                .map((f) => (
                  <p key={f.id} className="dar-doc-line">
                    {f.citation?.quote || f.raw_text}
                  </p>
                ))}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  void downloadDocumentDerived(documentId)
                    .then((blob) => downloadBlob(blob, doc.display_name || 'document.bin'))
                    .catch(() => setExportErr('Не удалось скачать файл'));
                }}
              >
                Скачать производный файл
              </Button>
            </section>
          ) : tab === 'risks' ? (
            <section className="dar-stack">
              {riskHits.length ? (
                riskHits.map((h) => (
                  <article key={`${h.rule_id}-${h.message}`} className={`dar-risk-card dar-risk-card--${h.severity === 'high' ? 'high' : 'medium'}`}>
                    <div className="dar-row dar-row--between">
                      <strong>{h.message}</strong>
                      <Badge tone={h.severity === 'high' ? 'danger' : 'warning'}>{formatSeverity(h.severity)}</Badge>
                    </div>
                    <p className="dar-muted">
                      Правило · {formatUncertainty(h.uncertainty)}
                    </p>
                    <details>
                      <summary>Технические подробности</summary>
                      <p className="dar-mono">{h.rule_id}</p>
                    </details>
                    <FindingFeedbackRow targetId={h.rule_id} targetType="rule_hit" />
                  </article>
                ))
              ) : (
                <p role="status">Срабатываний правил с повышенным приоритетом не найдено.</p>
              )}
            </section>
          ) : tab === 'conflicts' ? (
            <section className="dar-stack">
              {conflictHits.length ? (
                conflictHits.map((h) => (
                  <article key={`${h.rule_id}-c`} className="dar-panel">
                    <strong>{h.message}</strong>
                    <FindingFeedbackRow targetId={h.rule_id} targetType="rule_hit" />
                  </article>
                ))
              ) : (
                <p role="status">Структурных противоречий не обнаружено по текущим правилам.</p>
              )}
            </section>
          ) : (
            <div className={showSplit ? 'dar-workspace' : 'dar-stack'}>
              <section className="dar-stack">
                {filteredFindings.length ? (
                  filteredFindings.map((finding) => (
                    <div key={finding.id} className="dar-card dar-stack">
                      <FindingCard
                        title={formatEntityType(finding.entity_type)}
                        kind={finding.kind as 'fact' | 'inference'}
                        value={String(finding.normalized_value ?? finding.raw_text)}
                        uncertainty={formatUncertainty(finding.uncertainty_state)}
                        active={finding.id === activeFindingId}
                        onSelect={() => setActiveFindingId(finding.id)}
                      />
                      <ConfidenceIndicator value={finding.confidence} />
                      <p className="dar-muted">
                        {formatFindingKind(finding.kind)} · стр. {finding.citation.page}
                      </p>
                      <FindingFeedbackRow targetId={finding.id} targetType="finding" />
                    </div>
                  ))
                ) : (
                  <p role="status">Нет пунктов для выбранных фильтров.</p>
                )}
              </section>
              {showSplit ? <CitationPreview finding={activeFinding ?? null} page={activePage} /> : null}
            </div>
          )}
        </>
      ) : run?.status === 'failed' ? (
        <div className="dar-panel" role="alert">
          <p>Анализ завершился с ошибкой{run.error_code ? `: ${run.error_code}` : ''}.</p>
          <Button onClick={() => void onRetry()}>Повторить анализ</Button>
        </div>
      ) : !run ? (
        <div className="dar-panel">
          <p>Анализ ещё не запускался.</p>
          <Button onClick={() => void onRestart()}>Запустить анализ</Button>
        </div>
      ) : null}

      <DeleteDocumentDialog
        documentId={documentId}
        displayName={doc.display_name}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onDeleted={onBack}
      />
    </div>
  );
}

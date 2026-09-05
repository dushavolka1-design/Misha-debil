'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { Alert, Button, Checkbox, Dialog, FileDropzone, ScreenStateView, parseScreenState } from '@dar/ui';
import { useSearchParams } from 'next/navigation';

import { AnalysisProgressCard } from '../../../components/AnalysisProgressCard';
import { useToast } from '../../../components/Toast';
import {
  apiFetch,
  fetchDocument,
  fetchDocumentRuns,
  fetchDocuments,
  fetchUploadLimits,
  formatApiError,
  startAnalysis,
  type DocumentListItem,
  type UploadLimits,
} from '../../../lib/apiClient';
import { formatDocumentState } from '../../../lib/statusLabels';
import { getApiBase } from '../../../lib/apiBase';

type LegalItem = {
  id: string;
  consent_id: string;
  consent_version: string;
  content_hash: string;
};

function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${Math.round(n / (1024 * 1024))} МБ`;
  return `${Math.round(n / 1024)} КБ`;
}

function fileTypeLabel(file: File): string {
  if (file.type) return file.type;
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return 'application/pdf';
  if (ext === 'docx') return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  if (ext === 'png') return 'image/png';
  return 'image/jpeg';
}

type Props = {
  embedded?: boolean;
  initialRunId?: string | null;
  onOpenDocument?: (documentId: string, runId?: string | null) => void;
};

export default function UploadClient({ embedded = false, initialRunId = null, onOpenDocument }: Props) {
  const toast = useToast();
  const state = parseScreenState(useSearchParams().get('state'));
  const [medical, setMedical] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [medicalOpen, setMedicalOpen] = useState(false);
  const [medicalDoc, setMedicalDoc] = useState<LegalItem | null>(null);
  const [acceptedMedical, setAcceptedMedical] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(initialRunId);
  const [runReady, setRunReady] = useState(false);
  const [docState, setDocState] = useState<string | null>(null);
  const [limits, setLimits] = useState<UploadLimits | null>(null);
  const [limitsError, setLimitsError] = useState<string | null>(null);
  const [recent, setRecent] = useState<DocumentListItem[]>([]);
  const [recentError, setRecentError] = useState<string | null>(null);

  useEffect(() => {
    void apiFetch<LegalItem[]>('/legal/documents/active')
      .then((items) => {
        setMedicalDoc(items.find((i) => i.consent_id === 'special_categories.medical') ?? null);
      })
      .catch(() => undefined);
    void fetchUploadLimits()
      .then(setLimits)
      .catch((err) => setLimitsError(formatApiError(err, 'Не удалось загрузить лимиты')));
    void fetchDocuments()
      .then((docs) => {
        setRecentError(null);
        setRecent(docs.slice(0, 4));
      })
      .catch((err) => {
        setRecent([]);
        setRecentError(formatApiError(err, 'Не удалось загрузить список документов'));
      });
  }, []);

  useEffect(() => {
    if (!documentId || runId) return;
    let cancelled = false;
    let readySince: number | null = null;
    const poll = async () => {
      try {
        const doc = await fetchDocument(documentId);
        if (cancelled) return;
        setDocState(doc.state);
        if (doc.state === 'READY' || doc.state === 'ready') {
          if (!readySince) readySince = Date.now();
          const runs = await fetchDocumentRuns(documentId);
          if (cancelled) return;
          const latest = runs[runs.length - 1];
          if (latest) {
            setRunId(latest.run_id);
            return;
          }
          if (Date.now() - readySince > 12_000) {
            const started = await startAnalysis(documentId);
            if (!cancelled) setRunId(started.run_id);
          }
        }
      } catch {
        // polling errors shown on next user action
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 2500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [documentId, runId]);

  async function runAnalyze() {
    if (!file) {
      setActionError('Выберите файл PDF, DOCX, JPEG или PNG');
      return;
    }
    if (limits && file.size > limits.max_bytes) {
      setActionError(`Файл слишком большой. Максимум: ${formatBytes(limits.max_bytes)}`);
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      const gateBody = await apiFetch<{ allowed: boolean }>('/privacy/upload-gate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ potentially_medical: medical, filename: 'upload.bin' }),
      });
      if (!gateBody.allowed) {
        if (medical) {
          setMedicalOpen(true);
          setActionError('Нужно принять согласие на обработку медицинских данных');
        } else {
          setActionError('Не хватает обязательных согласий для загрузки');
        }
        return;
      }

      const intent = await apiFetch<{
        document_id: string;
        upload_url: string;
        headers?: Record<string, string>;
      }>('/documents/upload-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_filename: file.name,
          content_type: file.type || fileTypeLabel(file),
          size_bytes: file.size,
          potentially_medical: medical,
        }),
      });
      setDocumentId(intent.document_id);
      const status = await apiFetch<{ state: string }>(intent.upload_url, {
        method: 'PUT',
        headers: intent.headers || { 'Content-Type': file.type || fileTypeLabel(file) },
        body: file,
        retries: 0,
        timeoutMs: 60_000,
      });
      setDocState(status.state);
      toast.showSuccess('Файл загружен — начинается обработка');
    } catch (err) {
      setActionError(formatApiError(err, 'Не удалось загрузить файл'));
    } finally {
      setBusy(false);
    }
  }

  async function acceptMedical() {
    if (!medicalDoc || !acceptedMedical) return;
    await apiFetch('/privacy/consents/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        consent_id: medicalDoc.consent_id,
        consent_version: medicalDoc.consent_version,
        content_hash: medicalDoc.content_hash,
        locale: 'ru-RU',
      }),
    });
    setMedicalOpen(false);
    await runAnalyze();
  }

  return (
    <div>
      {!embedded ? (
        <>
          <h1 className="dar-page-title">Новый анализ</h1>
          <p className="dar-page-lead">PDF, DOCX или изображение — результат появится на этой странице.</p>
        </>
      ) : null}
      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <section className="dar-panel dar-panel--hero dar-stack" aria-labelledby="upload-hero-title">
              <h2 id="upload-hero-title" className="dar-subheading">
                Загрузите документ
              </h2>
            {limits ? (
              <p className="dar-form-note" role="note">
                Форматы: {limits.formats_label}. До {formatBytes(limits.max_bytes)}, не более {limits.max_pages}{' '}
                страниц. Обычное время обработки — 1–5 минут.
              </p>
            ) : limitsError ? (
              <Alert title="Не удалось загрузить лимиты" tone="warning">
                {limitsError}
              </Alert>
            ) : null}

            <FileDropzone
              status={busy ? 'scanning' : actionError ? 'error' : file ? 'selected' : 'idle'}
              fileName={file?.name ?? null}
              errorText={actionError}
              onFiles={(files) => {
                setFile(files.item(0));
                setActionError(null);
              }}
              accept=".pdf,.docx,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            />

            {file ? (
              <div className="dar-panel dar-panel--inset" role="status">
                <strong>{file.name}</strong>
                <p className="dar-doc-card__meta">
                  {formatBytes(file.size)} · {fileTypeLabel(file)}
                </p>
              </div>
            ) : null}

            <Checkbox
              id="upload-medical"
              checked={medical}
              onChange={setMedical}
              label="Документ может содержать медицинские / данные о здоровье"
            />

            <Button disabled={!file || busy} loading={busy} onClick={() => void runAnalyze()}>
              {busy ? 'Загрузка…' : 'Проанализировать'}
            </Button>
            </section>

            {actionError ? (
              <Alert title="Не удалось продолжить" tone="danger">
                {actionError}
                <div>
                  <Button variant="secondary" onClick={() => void runAnalyze()}>
                    Повторить
                  </Button>
                </div>
              </Alert>
            ) : null}

            {docState ? (
              <p role="status">Состояние документа: {formatDocumentState(docState)}</p>
            ) : null}

            {runId ? (
              <AnalysisProgressCard
                runId={runId}
                onReady={(docId, rid) => {
                  setDocumentId(docId);
                  setRunId(rid);
                  setRunReady(true);
                }}
              />
            ) : null}

            {runReady && runId && documentId ? (
              <div className="dar-row">
                <Button
                  variant="primary"
                  onClick={() => {
                    if (onOpenDocument) onOpenDocument(documentId, runId);
                  }}
                >
                  Открыть результат
                </Button>
                <Link className="dar-btn dar-btn--secondary" href="/app/analyzer?tab=documents">
                  Мои документы
                </Link>
              </div>
            ) : (
              <Link className="dar-btn dar-btn--ghost" href="/app/analyzer?tab=documents">
                Мои документы
              </Link>
            )}

            {recentError ? (
              <Alert title="Список документов недоступен" tone="danger">
                {recentError}
              </Alert>
            ) : null}

            {recent.length ? (
              <section className="dar-stack" aria-labelledby="recent-docs-title">
                <h2 id="recent-docs-title" className="dar-subheading">
                  Последние документы
                </h2>
                <ul className="dar-recent-grid">
                  {recent.map((doc) => (
                    <li key={doc.id}>
                      <button
                        type="button"
                        className="dar-recent-card"
                        onClick={() => onOpenDocument?.(doc.id, doc.latest_run_id)}
                      >
                        <strong>{doc.display_name}</strong>
                        <span className="dar-doc-card__meta">
                          {formatDocumentState(doc.state)} · {new Date(doc.updated_at).toLocaleString('ru-RU')}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <Dialog open={medicalOpen} title="Согласие на специальные категории" onClose={() => setMedicalOpen(false)}>
              <p>
                Для продолжения примите{' '}
                {medicalDoc ? (
                  <a href={`${getApiBase()}/legal/documents/${medicalDoc.id}/text`} target="_blank" rel="noreferrer">
                    {medicalDoc.consent_version}
                  </a>
                ) : (
                  'актуальную версию'
                )}
                . Сервис не ставит диагнозов.
              </p>
              <Checkbox
                id="med-accept"
                checked={acceptedMedical}
                onChange={setAcceptedMedical}
                label="Подтверждаю согласие на обработку потенциально медицинских данных"
              />
              <div className="dar-row">
                <Button disabled={!acceptedMedical} onClick={() => void acceptMedical()}>
                  Принять и проанализировать
                </Button>
                <Button variant="ghost" onClick={() => setMedicalOpen(false)}>
                  Отмена
                </Button>
              </div>
            </Dialog>
          </div>
        }
      />
    </div>
  );
}

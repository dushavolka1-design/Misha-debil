'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useSearchParams } from 'next/navigation';

import {
  Alert,
  Badge,
  Button,
  FormErrorSummary,
  Input,
  ScreenStateView,
  Skeleton,
  parseScreenState,
} from '@dar/ui';

import { SectionErrorBoundary } from '../../../../components/SectionErrorBoundary';
import { useToast } from '../../../../components/Toast';
import { getApiBase } from '../../../../lib/apiBase';
import { ApiError, apiFetch, downloadBlob, downloadGeneratedPdf, formatApiError } from '../../../../lib/apiClient';
import { checkAnswers, issueForField, normalizeField } from '../../../../lib/answerChecks';

type FieldMeta = {
  label: string;
  hint?: string;
  required?: boolean;
  user_editable?: boolean;
  manual_only?: boolean;
  multiline?: boolean;
};

type Section = {
  id: string;
  label: string;
  fields: Array<{ field_id: string } & FieldMeta>;
};

type ChecklistItem = { id: string; done: boolean; label: string };

type FillPackage = {
  available: boolean;
  unavailable_reason?: string;
  checklist_hint?: string;
  checklist?: ChecklistItem[];
  catalog?: {
    title: string;
    slug?: string;
    form_kind: string;
    edition: string;
    warning: string;
    official_url?: string | null;
    act_title?: string | null;
    appendix?: string | null;
    source: Record<string, unknown> | null;
    reviewed_at: string | null;
  };
  version?: {
    id: string;
    slug?: string;
    form_version: string;
    title: string;
    original_hash: string;
    download_basename?: string;
  };
  field_schema?: Record<string, FieldMeta>;
  sections?: Section[];
  underlay_url?: string;
  preview_title?: string;
  worksheet?: {
    available: boolean;
    mode?: string;
    version?: FillPackage['version'];
    field_schema?: Record<string, FieldMeta>;
    sections?: Section[];
    underlay_url?: string;
    preview_title?: string;
  };
};

type PreviewIssue = { field_id: string; message: string; severity: string };

type PreDownload = {
  title: string;
  edition: string;
  checked_at: string;
  preview_ok: boolean;
  missing_required: string[];
  manual_review_warning: string;
  can_download: boolean;
};

function fieldHighlight(field: FieldMeta): CSSProperties {
  if (field.manual_only || field.user_editable === false) {
    return { borderLeft: '4px solid var(--dar-color-text-secondary, #888)', paddingLeft: 12 };
  }
  if (field.required) {
    return { borderLeft: '4px solid var(--dar-color-warning, #c45c12)', paddingLeft: 12 };
  }
  return { borderLeft: '4px solid var(--dar-color-border, #ddd)', paddingLeft: 12 };
}

function FormFillInner({ formId }: { formId: string }) {
  const toast = useToast();
  const state = parseScreenState(useSearchParams().get('state'));
  const [pkg, setPkg] = useState<FillPackage | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [generatedId, setGeneratedId] = useState<string | null>(null);
  const [preDownload, setPreDownload] = useState<PreDownload | null>(null);
  const [showDownloadDialog, setShowDownloadDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [fieldNotes, setFieldNotes] = useState<Record<string, string>>({});
  const [stepAttempted, setStepAttempted] = useState(false);
  const skipAutosave = useRef(true);

  const loadPackage = useCallback(async () => {
    setError(null);
    try {
      const data = await apiFetch<FillPackage>(`/forms/fill/by-catalog/${formId}`);
      setPkg(data);
      if (data.available || data.worksheet?.available) {
        try {
          const draftData = await apiFetch<{ draft?: { answers?: Record<string, string> } }>(
            `/forms/fill/drafts?catalog_form_id=${formId}`,
          );
          if (draftData?.draft?.answers) {
            const slug =
              (data.available ? data.version?.slug : data.worksheet?.version?.slug) || data.catalog?.slug || '';
            const raw = draftData.draft.answers;
            const next: Record<string, string> = {};
            for (const [id, val] of Object.entries(raw)) {
              next[id] = slug ? normalizeField(slug, id, val || '', { onBlur: true }).value : val || '';
            }
            setAnswers(next);
          }
        } catch (err) {
          if (err instanceof ApiError && err.code !== 'unauthorized') {
            setError(err.detail || err.message);
          }
        }
      }
    } catch (err) {
      setError(formatApiError(err, 'Ошибка загрузки'));
    }
  }, [formId]);

  useEffect(() => {
    void loadPackage();
  }, [loadPackage]);

  const worksheet = pkg?.worksheet;
  const usingWorksheet = Boolean(pkg && !pkg.available && worksheet?.available);
  const fillable = Boolean(pkg?.available || usingWorksheet);
  const versionId = (pkg?.available ? pkg.version?.id : worksheet?.version?.id) ?? '';
  const isGov = pkg?.catalog?.form_kind === 'government_form';
  const sections = (pkg?.available ? pkg.sections : worksheet?.sections) || [];
  const underlayPath = pkg?.available ? pkg.underlay_url : worksheet?.underlay_url;
  const previewTitle = pkg?.available ? pkg.preview_title : worksheet?.preview_title;
  const formSlug = (pkg?.available ? pkg.version?.slug : worksheet?.version?.slug) || pkg?.catalog?.slug || '';
  const liveSchema = (pkg?.available ? pkg.field_schema : worksheet?.field_schema) || {};
  const steps = useMemo(() => [...sections.map((s) => s.label), 'Проверка'], [sections]);

  const liveIssues = useMemo(
    () => (formSlug ? checkAnswers(formSlug, answers, liveSchema) : []),
    [answers, formSlug, liveSchema],
  );

  const previewErrors = useMemo(() => {
    const fromPreview = ((preview?.issues as PreviewIssue[]) || [])
      .filter((i) => i.severity === 'error')
      .map((i) => ({ id: i.field_id, message: i.message }));
    const live = liveIssues.map((i) => ({ id: i.field_id, message: i.message }));
    const byId = new Map<string, { id: string; message: string }>();
    for (const item of [...fromPreview, ...live]) byId.set(item.id, item);
    return [...byId.values()];
  }, [preview, liveIssues]);

  const saveDraft = useCallback(
    async (silent = false) => {
      if (!pkg?.available && !pkg?.worksheet?.available) return;
      setSaving(true);
      try {
        await apiFetch('/forms/fill/drafts', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ catalog_form_id: formId, answers }),
        });
        if (!silent) toast.showSuccess('Черновик сохранён');
      } catch (err) {
        setError(formatApiError(err, 'Не удалось сохранить черновик'));
      } finally {
        setSaving(false);
      }
    },
    [answers, formId, pkg?.available, pkg?.worksheet?.available, toast],
  );

  useEffect(() => {
    if (!pkg?.available && !pkg?.worksheet?.available) return;
    if (skipAutosave.current) {
      skipAutosave.current = false;
      return;
    }
    const handle = window.setTimeout(() => {
      void saveDraft(true);
    }, 900);
    return () => window.clearTimeout(handle);
  }, [answers, pkg?.available, pkg?.worksheet?.available, saveDraft]);

  useEffect(() => {
    if (!underlayPath) {
      setPreviewUrl(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    void (async () => {
      try {
        const res = await fetch(`${getApiBase()}${underlayPath}`, { credentials: 'include' });
        if (!res.ok) return;
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      } catch {
        if (!cancelled) setPreviewUrl(null);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [underlayPath]);

  const applyField = useCallback(
    (fieldId: string, raw: string, source: 'change' | 'blur') => {
      const corrected = formSlug
        ? normalizeField(formSlug, fieldId, raw, { onBlur: source === 'blur' })
        : { value: raw };
      if (source === 'blur') {
        setTouched((t) => ({ ...t, [fieldId]: true }));
      }
      setAnswers((prev) => ({ ...prev, [fieldId]: corrected.value }));
      setFieldNotes((prev) => {
        const copy = { ...prev };
        if (corrected.message) copy[fieldId] = corrected.message;
        else delete copy[fieldId];
        return copy;
      });
    },
    [formSlug],
  );

  function jumpToField(fieldId: string) {
    const idx = sections.findIndex((s) => s.fields.some((f) => f.field_id === fieldId));
    if (idx >= 0) setStep(idx);
    window.setTimeout(() => document.getElementById(fieldId)?.focus(), 0);
  }

  function goNext() {
    const section = sections[step];
    if (!section) {
      setStep((s) => Math.min(steps.length - 1, s + 1));
      return;
    }
    const nextAnswers = { ...answers };
    const notes: Record<string, string> = {};
    for (const field of section.fields) {
      if (field.user_editable === false || field.manual_only) continue;
      const raw = nextAnswers[field.field_id] || '';
      if (!formSlug || !raw.trim()) continue;
      const corrected = normalizeField(formSlug, field.field_id, raw, { onBlur: true });
      if (corrected.value !== raw) {
        nextAnswers[field.field_id] = corrected.value;
        if (corrected.message) notes[field.field_id] = corrected.message;
      }
    }
    if (Object.keys(notes).length) {
      setAnswers(nextAnswers);
      setFieldNotes((prev) => ({ ...prev, ...notes }));
    }
    const issues = formSlug ? checkAnswers(formSlug, nextAnswers, liveSchema) : liveIssues;
    const blocking: string[] = [];
    for (const field of section.fields) {
      if (field.user_editable === false || field.manual_only) continue;
      const val = (nextAnswers[field.field_id] || '').trim();
      if (field.required && !val) blocking.push(field.field_id);
      else if (issueForField(issues, field.field_id)) blocking.push(field.field_id);
    }
    if (blocking.length) {
      setStepAttempted(true);
      setTouched((t) => {
        const copy = { ...t };
        for (const id of blocking) copy[id] = true;
        return copy;
      });
      const first = blocking[0];
      if (first) document.getElementById(first)?.focus();
      return;
    }
    setStepAttempted(false);
    setStep((s) => Math.min(steps.length - 1, s + 1));
  }

  async function runPreview(): Promise<boolean> {
    if (!versionId) return false;
    setError(null);
    try {
      const data = await apiFetch<Record<string, unknown>>('/forms/fill/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ form_version_id: versionId, answers }),
      });
      setPreview(data);
      void saveDraft(true);
      return Boolean(data.ok);
    } catch (err) {
      setError(formatApiError(err, 'Ошибка предпросмотра'));
      setPreview(null);
      return false;
    }
  }

  async function openDownloadDialog() {
    if (!versionId) return;
    const previewOk = await runPreview();
    if (!previewOk) {
      setShowDownloadDialog(false);
      setPreDownload(null);
      return;
    }
    try {
      const data = await apiFetch<PreDownload>('/forms/fill/pre-download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ form_version_id: versionId, answers }),
      });
      setPreDownload(data);
      setShowDownloadDialog(true);
    } catch (err) {
      setError(formatApiError(err, 'Проверка перед скачиванием не прошла'));
    }
  }

  async function generate() {
    if (!versionId || !preDownload?.can_download) return;
    setError(null);
    try {
      const data = await apiFetch<{ generated_id: string; preview: Record<string, unknown> }>('/forms/fill/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ form_version_id: versionId, answers, catalog_form_id: formId }),
      });
      setGeneratedId(data.generated_id);
      setPreview(data.preview);
      setShowDownloadDialog(false);
      toast.showSuccess('Документ сформирован — можно скачать');
    } catch (err) {
      setError(formatApiError(err, 'Ошибка генерации'));
    }
  }

  async function downloadPdf() {
    if (!generatedId) return;
    try {
      const { blob, filename } = await downloadGeneratedPdf(generatedId);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(formatApiError(err, 'Не удалось скачать PDF'));
    }
  }

  if (error && !pkg) {
    return (
      <Alert title="Не удалось открыть форму" tone="danger">
        {error}
      </Alert>
    );
  }

  if (!pkg) {
    return <Skeleton height={320} />;
  }

  if (!fillable) {
    const officialUrl = pkg.catalog?.official_url;
    return (
      <div className="dar-stack">
        <h1 className="dar-page-title">{pkg.catalog?.title || 'Шаблон недоступен'}</h1>
        <Alert title="Почему официальный бланк недоступен" tone="warning">
          {pkg.unavailable_reason}
        </Alert>
        {pkg.catalog?.act_title ? <p className="dar-muted">{pkg.catalog.act_title}</p> : null}
        {officialUrl ? (
          <p>
            Официальный источник:{' '}
            <a href={officialUrl} className="dar-link" target="_blank" rel="noreferrer">
              {officialUrl}
            </a>
          </p>
        ) : null}
        {pkg.checklist?.length ? (
          <section className="dar-panel dar-stack">
            <h2 className="dar-subheading" style={{ margin: 0 }}>
              Что нужно для заполнения бланка госоргана
            </h2>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {pkg.checklist.map((item) => (
                <li key={item.id}>
                  {item.done ? 'Готово: ' : 'Ожидается: '}
                  {item.label}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <Alert title="Что можно сделать" tone="info">
          {pkg.checklist_hint}{' '}
          <Link href="/app/generator?tab=wizard" className="dar-link">
            Открыть мастер документов
          </Link>
        </Alert>
        <Link href="/app/generator?tab=templates" className="dar-btn dar-btn--secondary">
          К каталогу шаблонов
        </Link>
      </div>
    );
  }

  const onLastStep = step >= sections.length;
  const currentSection = sections[step];
  const edition = pkg.available ? pkg.version?.form_version : worksheet?.version?.form_version;
  const sectionFieldIds = new Set((currentSection?.fields || []).map((f) => f.field_id));
  const visibleErrors = onLastStep
    ? previewErrors
    : previewErrors.filter((e) => sectionFieldIds.has(e.id));

  return (
    <div>
      <div className="dar-row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="dar-page-title">{pkg.catalog?.title}</h1>
          <p className="dar-page-lead">
            {usingWorksheet
              ? 'Сверьте сведения с документами. Условия использования — в пользовательском соглашении.'
              : isGov
                ? 'Государственная форма'
                : 'Собственный шаблон сервиса'}{' '}
            · редакция {edition}
          </p>
        </div>
        <Badge tone={usingWorksheet || !isGov ? 'warning' : 'info'}>
          {usingWorksheet ? 'Сведения' : isGov ? 'Госформа' : 'Памятка сервиса'}
        </Badge>
      </div>

      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <p className="dar-form-note" role="note">
              Редакция {edition}
              {pkg.catalog?.reviewed_at ? ` · проверено ${new Date(pkg.catalog.reviewed_at).toLocaleDateString('ru-RU')}` : ''}
            </p>
            {pkg.catalog?.warning ? <p className="dar-muted">{pkg.catalog.warning}</p> : null}
            {pkg.catalog?.official_url ? (
              <p>
                Официальный источник:{' '}
                <a href={pkg.catalog.official_url} className="dar-link" target="_blank" rel="noreferrer">
                  {pkg.catalog.official_url}
                </a>
              </p>
            ) : null}
            {usingWorksheet || fillable ? (
              <Alert title="Проверка при вводе" tone="info">
                Ошибки показываются сразу в поле: гражданство, написание «Паспорт», номера с карты. Однозначные
                опечатки и формулировку заявления сервис подставляет сам. Исправляйте на этом шаге, не в конце.
              </Alert>
            ) : null}
            <ol className="dar-row" style={{ flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: 0 }}>
              {steps.map((label, idx) => (
                <li key={label}>
                  <Badge tone={idx === step ? 'info' : 'neutral'}>
                    {idx + 1}. {label}
                  </Badge>
                </li>
              ))}
            </ol>
            <div
              onClick={(e) => {
                const link = (e.target as HTMLElement).closest('a');
                const id = link?.getAttribute('href')?.replace('#', '');
                if (!id) return;
                e.preventDefault();
                jumpToField(id);
              }}
            >
              <FormErrorSummary errors={visibleErrors} />
            </div>
            {!onLastStep && currentSection ? (
              <section className="dar-panel dar-stack">
                <h2 className="dar-subheading">{currentSection.label}</h2>
                {currentSection.fields.map((field) => {
                  const editable = field.user_editable !== false && !field.manual_only;
                  if (!editable) {
                    return (
                      <div key={field.field_id} className="dar-form-note" style={fieldHighlight(field)}>
                        <strong>{field.label}.</strong> {field.hint || 'Заполняется вручную после печати. Сервис это поле не ставит.'}
                      </div>
                    );
                  }
                  const liveError = issueForField(liveIssues, field.field_id);
                  const empty = !(answers[field.field_id] || '').trim();
                  const requiredError =
                    field.required && empty && (touched[field.field_id] || stepAttempted)
                      ? 'Заполните поле по документу.'
                      : undefined;
                  const fieldError = liveError || requiredError;
                  const hint = [field.hint, fieldNotes[field.field_id]].filter(Boolean).join(' ');
                  if (field.multiline) {
                    return (
                      <div key={field.field_id} className="dar-field" style={fieldHighlight(field)}>
                        <label className="dar-field__label" htmlFor={field.field_id}>
                          {field.label}
                          {field.required ? ' *' : ''}
                        </label>
                        <textarea
                          id={field.field_id}
                          className="dar-input dar-textarea"
                          value={answers[field.field_id] || ''}
                          onChange={(e) => applyField(field.field_id, e.target.value, 'change')}
                          onBlur={(e) => applyField(field.field_id, e.target.value, 'blur')}
                          required={field.required}
                          aria-invalid={Boolean(fieldError) || undefined}
                          rows={4}
                        />
                        {hint ? (
                          <p className="dar-field__hint" id={`${field.field_id}-hint`}>
                            {hint}
                          </p>
                        ) : null}
                        {fieldError ? (
                          <p className="dar-field__error" id={`${field.field_id}-error`} role="alert">
                            {fieldError}
                          </p>
                        ) : null}
                      </div>
                    );
                  }
                  return (
                    <div key={field.field_id} style={fieldHighlight(field)}>
                      <Input
                        id={field.field_id}
                        label={`${field.label}${field.required ? ' *' : ''}`}
                        hint={hint || undefined}
                        error={fieldError}
                        value={answers[field.field_id] || ''}
                        onChange={(e) => applyField(field.field_id, e.target.value, 'change')}
                        onBlur={(e) => applyField(field.field_id, e.target.value, 'blur')}
                        required={field.required}
                      />
                    </div>
                  );
                })}
              </section>
            ) : (
              <section className="dar-panel dar-stack">
                <h2 style={{ margin: 0, fontSize: '1.05rem' }}>Проверка перед файлом</h2>
                <p className="dar-muted">
                  {previewErrors.length
                    ? 'На шагах выше остались замечания — вернитесь к полю по ссылке в списке.'
                    : preview
                      ? preview.ok
                        ? 'Поля прошли проверку'
                        : 'Исправьте замечания перед генерацией'
                      : 'Если поля на предыдущих шагах без ошибок, сформируйте PDF.'}
                </p>
              </section>
            )}
            {error ? (
              <p className="dar-field__error" role="alert">
                {error}
              </p>
            ) : null}
            {versionId && (previewUrl || underlayPath) ? (
              <details className="dar-panel">
                <summary>{previewTitle || 'Макет PDF'}</summary>
                <object
                  title={previewTitle || 'Макет формы'}
                  data={previewUrl || `${getApiBase()}${underlayPath}`}
                  type="application/pdf"
                  className="dar-iframe-preview"
                >
                  <a href={previewUrl || `${getApiBase()}${underlayPath}`} target="_blank" rel="noreferrer">
                    Открыть макет PDF
                  </a>
                </object>
              </details>
            ) : null}
            {generatedId ? (
              <div className="dar-row">
                <Button onClick={() => void downloadPdf()}>Скачать заполненный PDF</Button>
                <Link href="/app/generator?tab=created" className="dar-btn dar-btn--secondary">
                  История документов
                </Link>
              </div>
            ) : null}
            {showDownloadDialog && preDownload ? (
              <div className="dar-panel dar-stack" role="dialog" aria-labelledby="predownload-title">
                <h2 id="predownload-title" style={{ margin: 0 }}>
                  Перед скачиванием
                </h2>
                <p>
                  <strong>{preDownload.title}</strong> · редакция {preDownload.edition}
                </p>
                <p>Дата проверки: {new Date(preDownload.checked_at).toLocaleString('ru-RU')}</p>
                {usingWorksheet || !pkg.catalog?.source ? (
                  <p>Перед подачей сверьте файл с документами. Условия использования — в пользовательском соглашении.</p>
                ) : (
                  <p>Официальный источник указан в карточке шаблона.</p>
                )}
                {preDownload.missing_required.length > 0 ? (
                  <div className="dar-form-note">
                    <strong>Незаполненные обязательные поля:</strong>
                    <ul>
                      {preDownload.missing_required.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <p className="dar-muted">{preDownload.manual_review_warning}</p>
                <div className="dar-row">
                  <Button onClick={() => void generate()} disabled={!preDownload.can_download}>
                    Подтвердить и сгенерировать
                  </Button>
                  <Button variant="ghost" onClick={() => setShowDownloadDialog(false)}>
                    Отмена
                  </Button>
                </div>
              </div>
            ) : null}
            <div
              className="dar-row"
              style={{
                position: 'sticky',
                bottom: 0,
                background: 'var(--dar-color-bg, #fff)',
                padding: '12px 0',
                borderTop: '1px solid var(--dar-border, #ddd)',
                zIndex: 2,
                justifyContent: 'space-between',
              }}
            >
              <Button variant="secondary" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
                Назад
              </Button>
              <div className="dar-row">
                <Button variant="secondary" onClick={() => void saveDraft(false)} disabled={saving}>
                  Сохранить черновик
                </Button>
                {onLastStep ? (
                  <>
                    <Button variant="secondary" onClick={() => void runPreview()}>
                      Проверить поля
                    </Button>
                    <Button onClick={() => void openDownloadDialog()} disabled={!versionId}>
                      {usingWorksheet ? 'Скачать PDF' : 'Сгенерировать PDF'}
                    </Button>
                  </>
                ) : (
                  <Button onClick={() => goNext()}>Далее</Button>
                )}
              </div>
            </div>
          </div>
        }
      />
    </div>
  );
}

export default function FormFillClient({ formId }: { formId: string }) {
  return (
    <SectionErrorBoundary sectionLabel="Заполнение">
      <FormFillInner formId={formId} />
    </SectionErrorBoundary>
  );
}

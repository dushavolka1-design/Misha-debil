'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { Badge, Button, Checkbox, Input, ScreenStateView, Tabs, parseScreenState } from '@dar/ui';

import { formatOutcome, formatStatus } from '../../../lib/statusLabels';
import { useToast } from '../../../components/Toast';
import {
  ApiError,
  apiFetch,
  downloadBlob,
  exportEntryChecklistPdf,
  fetchGenerationCapabilities,
  fetchVisaRegimes,
  formatApiError,
} from '../../../lib/apiClient';

type Regime = { id: string; label: string; source_slug: string };

type EvalResult = {
  snapshot_id: string;
  pack_version: string;
  disclaimer: string;
  unknown_case: boolean;
  activated_rule_ids: string[];
  freshness_blocked_rules: string[];
  stages: Record<string, Array<Record<string, unknown>>>;
  reviewed_at?: string | null;
  recommended_forms?: Array<{
    form_id: string;
    title: string;
    reason: string;
    fill_ready: boolean;
    form_kind: string;
    unavailable_reason: string | null;
    category_label: string;
  }>;
};

const STAGE_LABELS: Record<string, string> = {
  before_trip: 'До поездки',
  at_border: 'При пересечении границы',
  after_entry: 'После въезда',
  work_study: 'Работа / учёба',
  extension_change: 'Продление / изменение',
  medical_dactylo: 'Мед. / дактилоскопия',
};

export default function EntryWizardClient({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast();
  const state = parseScreenState(useSearchParams().get('state'));
  const [regimes, setRegimes] = useState<Regime[]>([]);
  const [consent, setConsent] = useState(false);
  const [citizenship, setCitizenship] = useState('');
  const [second, setSecond] = useState(false);
  const [ageBand, setAgeBand] = useState<'adult' | 'minor'>('adult');
  const [visa, setVisa] = useState('');
  const [purpose, setPurpose] = useState('tourism');
  const [stayDays, setStayDays] = useState('30');
  const [entryDate, setEntryDate] = useState('');
  const [eaeu, setEaeu] = useState(false);
  const [invitation, setInvitation] = useState(false);
  const [host, setHost] = useState('none');
  const [region, setRegion] = useState('');
  const [extension, setExtension] = useState(false);
  const [dactylo, setDactylo] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState('before_trip');
  const [generationReady, setGenerationReady] = useState(false);
  const [regimeError, setRegimeError] = useState<string | null>(null);

  useEffect(() => {
    void fetchVisaRegimes()
      .then((data) => {
        setRegimes(data);
        setRegimeError(null);
        if (data[0]) setVisa(data[0].id);
      })
      .catch((err) => {
        setRegimes([]);
        setRegimeError(formatApiError(err, 'Не удалось загрузить визовые режимы'));
      });
    void fetchGenerationCapabilities()
      .then((caps) => setGenerationReady(Boolean(caps.generation_ready)))
      .catch(() => setGenerationReady(false));
  }, []);

  const body = useMemo(
    () => ({
      citizenship: citizenship.trim() || 'unknown',
      second_citizenship: second,
      age_band: ageBand,
      visa_regime_id: visa || null,
      purpose,
      planned_stay_days: stayDays ? Number(stayDays) : null,
      planned_entry_date: entryDate || null,
      eaeu_member: eaeu,
      invitation,
      host_type: host,
      region_code: region || null,
      special_statuses: dactylo ? ['medical_dactylo_applicable'] : [],
      plans_extension_or_change: extension,
      timezone: 'Europe/Moscow',
      draft_consent: consent,
    }),
    [citizenship, second, ageBand, visa, purpose, stayDays, entryDate, eaeu, invitation, host, region, dactylo, extension, consent],
  );

  async function evaluate() {
    setError(null);
    try {
      const data = await apiFetch<EvalResult>('/entry/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      setResult(data);
      const firstStage = Object.keys(STAGE_LABELS).find((k) => (data.stages?.[k] || []).length);
      if (firstStage) setTab(firstStage);
    } catch (err) {
      setError(formatApiError(err, 'Ошибка расчёта'));
    }
  }

  async function saveDraft() {
    setError(null);
    if (!consent) {
      setError('Черновик сохраняется только с согласием');
      return;
    }
    try {
      await apiFetch('/entry/drafts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      toast.showSuccess('Черновик анкеты сохранён');
    } catch (err) {
      setError(formatApiError(err, 'Не удалось сохранить черновик'));
    }
  }

  async function refresh() {
    if (!result?.snapshot_id) return;
    try {
      const data = await apiFetch<EvalResult>(`/entry/snapshots/${result.snapshot_id}/refresh`, { method: 'POST' });
      setResult(data);
    } catch (err) {
      setError(formatApiError(err, 'Не удалось обновить чеклист'));
    }
  }

  async function downloadChecklist() {
    if (!result?.snapshot_id) return;
    try {
      const blob = await exportEntryChecklistPdf(result.snapshot_id);
      downloadBlob(blob, 'checklist-informational.pdf');
      toast.showSuccess('Чеклист сохранён');
    } catch (err) {
      setError(formatApiError(err, 'Не удалось скачать чеклист'));
    }
  }

  function renderStageSteps(stageId: string) {
    const steps = result?.stages[stageId] || [];
    if (!steps.length) {
      return <p className="dar-muted">Для этой стадии нет шагов по вашим ответам.</p>;
    }
    return (
      <div className="dar-stack">
        {steps.map((step) => {
          const deadline = step.deadline as { explanation?: string } | undefined;
          const sources = (step.official_sources as Array<{ title?: string; official_url?: string; state?: string }>) || [];
          const fee = step.fee as { available?: boolean; message?: string; amount?: unknown; currency?: string } | undefined;
          return (
            <article key={String(step.rule_id)} className="dar-panel">
              <div className="dar-row" style={{ justifyContent: 'space-between' }}>
                <strong>{String(step.title)}</strong>
                <Badge tone={step.needs_review ? 'warning' : 'success'}>
                  {step.needs_review ? 'Требует проверки' : formatOutcome(String(step.outcome))}
                </Badge>
              </div>
              <p>Кто выполняет: {String(step.actor)}</p>
              <p>Что подготовить: {String(step.prepare)}</p>
              <p>Срок: {deadline?.explanation || 'Уточняется по официальному источнику'}</p>
              <p>Куда обратиться: {String(step.authority)}</p>
              {step.as_of ? <p>Проверено: {String(step.as_of)}</p> : null}
              {String(step.exceptions) ? <p>Исключения: {String(step.exceptions)}</p> : null}
              {sources.length > 0 ? (
                <div>
                  <p style={{ marginBottom: 4 }}>Официальные источники:</p>
                  <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                    {sources.map((src, i) => (
                      <li key={`${String(step.rule_id)}-${i}`}>
                        {src.official_url ? (
                          <a href={src.official_url} target="_blank" rel="noreferrer">
                            {src.title || src.official_url}
                          </a>
                        ) : (
                          src.title || 'Источник на проверке'
                        )}
                        {src.state ? ` · ${formatStatus(String(src.state))}` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fee ? (
                <p>
                  Пошлина:{' '}
                  {fee.available
                    ? `${String(fee.amount ?? '—')} ${String(fee.currency ?? '')}`.trim()
                    : fee.message || 'Уточните на официальном ресурсе'}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    );
  }

  return (
    <div>
      {!embedded ? (
        <>
          <h1 className="dar-page-title">Мастер въезда и пребывания</h1>
          <p className="dar-page-lead">
            Ответьте на несколько вопросов — получите персональный чеклист шагов. Сервис не гарантирует допуск через
            границу.
          </p>
        </>
      ) : null}
      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <div className="dar-panel dar-stack">
              <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Анкета</h2>
              <Input
                id="citizenship"
                label="Гражданство"
                value={citizenship}
                onChange={(e) => setCitizenship(e.target.value)}
                hint="Код страны или «не указано», если не уверены"
                placeholder="Например: UZ, TJ, KG"
              />
              <Checkbox id="second" checked={second} onChange={setSecond} label="Есть второе гражданство" />
              <label className="dar-field">
                <span className="dar-field__label">Возраст</span>
                <select className="dar-input" value={ageBand} onChange={(e) => setAgeBand(e.target.value as 'adult' | 'minor')}>
                  <option value="adult">Совершеннолетний</option>
                  <option value="minor">Несовершеннолетний</option>
                </select>
              </label>
              <label className="dar-field">
                <span className="dar-field__label">Визовый режим</span>
                <select className="dar-input" value={visa} onChange={(e) => setVisa(e.target.value)}>
                  {regimes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="dar-field">
                <span className="dar-field__label">Цель</span>
                <select className="dar-input" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
                  <option value="tourism">Туризм / частный визит</option>
                  <option value="work">Работа</option>
                  <option value="study">Учёба</option>
                  <option value="family">Семья</option>
                  <option value="other">Иное</option>
                </select>
              </label>
              <Input id="stay" label="Планируемый срок (дней)" value={stayDays} onChange={(e) => setStayDays(e.target.value)} />
              <Input id="entry" label="Дата въезда" type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} />
              <Checkbox id="eaeu" checked={eaeu} onChange={setEaeu} label="ЕАЭС" />
              <Checkbox id="inv" checked={invitation} onChange={setInvitation} label="Есть приглашение" />
              <label className="dar-field">
                <span className="dar-field__label">Принимающая сторона</span>
                <select className="dar-input" value={host} onChange={(e) => setHost(e.target.value)}>
                  <option value="none">Нет / не применимо</option>
                  <option value="individual">Физлицо</option>
                  <option value="org">Организация</option>
                </select>
              </label>
              <Input id="region" label="Регион / адрес (опционально)" value={region} onChange={(e) => setRegion(e.target.value)} />
              <Checkbox id="ext" checked={extension} onChange={setExtension} label="Планирую продление / смену обстоятельств" />
              <Checkbox id="dac" checked={dactylo} onChange={setDactylo} label="Возможны медосмотр или дактилоскопия" />
              <Checkbox id="consent" checked={consent} onChange={setConsent} label="Согласен сохранить черновик анкеты" />
              <div className="dar-row">
                <Button onClick={() => void evaluate()}>Сформировать чеклист</Button>
                <Button variant="secondary" onClick={() => void saveDraft()}>
                  Сохранить черновик
                </Button>
              </div>
              {error ? (
                <p className="dar-field__error" role="alert">
                  {error}
                </p>
              ) : null}
              {regimeError ? (
                <p className="dar-field__error" role="alert">
                  {regimeError}
                </p>
              ) : null}
            </div>

            {result ? (
              <div className="dar-stack">
                {result.unknown_case ? (
                  <p className="dar-form-note" role="status">
                    Гражданство не указано — показаны только общие рекомендации без персонального списка документов.
                  </p>
                ) : null}
                <p className="dar-muted">{result.disclaimer}</p>
                {result.reviewed_at ? (
                  <p className="dar-muted">Дата проверки правил: {result.reviewed_at}</p>
                ) : null}
                {(result.recommended_forms || []).length > 0 ? (
                  <section className="dar-panel dar-stack">
                    <h2 style={{ margin: 0, fontSize: '1.05rem' }}>Рекомендуемые шаблоны</h2>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 10 }}>
                      {result.recommended_forms!.map((form) => (
                        <li key={form.form_id} className="dar-panel">
                          <div className="dar-row" style={{ justifyContent: 'space-between' }}>
                            <strong>{form.title}</strong>
                            <Badge tone={form.form_kind === 'medical_memo' ? 'warning' : 'info'}>
                              {form.category_label}
                            </Badge>
                          </div>
                          <p style={{ margin: '8px 0' }}>{form.reason}</p>
                          {form.fill_ready && !form.unavailable_reason && generationReady ? (
                            <Link href={`/app/forms/${form.form_id}`} className="dar-btn dar-btn--primary dar-btn--sm">
                              Заполнить
                            </Link>
                          ) : form.form_kind === 'government_form' ? (
                            <Link href={`/app/forms/${form.form_id}`} className="dar-btn dar-btn--primary dar-btn--sm">
                              Подготовить сведения
                            </Link>
                          ) : (
                            <p className="dar-muted">{form.unavailable_reason || 'Шаблон пока недоступен для заполнения'}</p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}
                <div className="dar-row">
                  {result.freshness_blocked_rules.length ? (
                    <Badge tone="warning">Часть правил устарела — проверьте источники</Badge>
                  ) : null}
                  <Button variant="secondary" onClick={() => void refresh()}>
                    Обновить чеклист
                  </Button>
                  <Button variant="secondary" onClick={() => void downloadChecklist()}>
                    Скачать чеклист PDF
                  </Button>
                </div>
                <Tabs
                  key={result.snapshot_id}
                  defaultValue={tab}
                  onChange={setTab}
                  items={Object.entries(STAGE_LABELS).map(([id, label]) => ({
                    value: id,
                    label: `${label}${result.stages?.[id]?.length ? ` (${result.stages[id].length})` : ''}`,
                    panel: renderStageSteps(id),
                  }))}
                />
              </div>
            ) : null}
          </div>
        }
      />
    </div>
  );
}

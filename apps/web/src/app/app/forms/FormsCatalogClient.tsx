'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';

import {
  Alert,
  Button,
  EmptyState,
  Icon,
  Input,
  ScreenStateView,
  TemplateCard,
  TemplateCardSkeleton,
  parseScreenState,
} from '@dar/ui';

import { ServiceUnavailable } from '../../../components/ServiceUnavailable';
import {
  ApiError,
  fetchForms,
  fetchGenerationCapabilities,
  formatApiError,
  type FormCard,
  type GenerationCapabilities,
} from '../../../lib/apiClient';
import { formatStatus } from '../../../lib/statusLabels';

const CATEGORIES = [
  { id: '', label: 'Все категории' },
  { id: 'entry_stay', label: 'Въезд и пребывание' },
  { id: 'work', label: 'Работа' },
  { id: 'rvp_vnz', label: 'РВП и ВНЖ' },
  { id: 'medical', label: 'Медицинские памятки' },
];

function statusTone(status: string, fillReady: boolean): 'success' | 'warning' | 'info' {
  if (fillReady) return 'success';
  if (status === 'published') return 'info';
  return 'warning';
}

export default function FormsCatalogClient({ embedded = false }: { embedded?: boolean }) {
  const state = parseScreenState(useSearchParams().get('state'));
  const [forms, setForms] = useState<FormCard[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState<ApiError | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<GenerationCapabilities | null>(null);

  const loadForms = useCallback(
    async (signal?: AbortSignal) => {
      setConnectionError(null);
      setLoadError(null);
      try {
        const q = new URLSearchParams();
        if (category) q.set('category', category);
        if (search.trim()) q.set('search', search.trim());
        const [data, caps] = await Promise.all([
          fetchForms(`${q.toString() ? `?${q}` : ''}`, signal),
          fetchGenerationCapabilities().catch(() => null),
        ]);
        setForms(data);
        if (caps) setCapabilities(caps);
      } catch (err) {
        if (signal?.aborted || (err instanceof ApiError && err.code === 'aborted')) {
          return;
        }
        if (err instanceof ApiError && err.isConnectionError) {
          setConnectionError(err);
          return;
        }
        setLoadError(formatApiError(err, 'Не удалось загрузить каталог шаблонов'));
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [category, search],
  );

  useEffect(() => {
    const controller = new AbortController();
    const delay = search.trim() ? 350 : 0;
    const timer = window.setTimeout(() => {
      void loadForms(controller.signal);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      if (delay > 0) controller.abort();
    };
  }, [loadForms, search]);

  const filtered = useMemo(() => forms, [forms]);

  if (connectionError?.isConnectionError) {
    return <ServiceUnavailable title="Каталог недоступен" onRetry={loadForms} />;
  }

  return (
    <div>
      {!embedded ? (
        <>
          <h1 className="dar-page-title">Каталог форм</h1>
          <p className="dar-page-lead">Официальные шаблоны и памятки сервиса.</p>
        </>
      ) : null}
      <ScreenStateView
        state={state}
        ready={
          <div className="dar-stack">
            <Input
              id="form-search"
              label="Какой документ вам нужен?"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Например: уведомление о прибытии, патент, РВП"
              leading={<Icon icon={Search} size={18} />}
            />
            <div className="dar-chip-row" role="group" aria-label="Категории">
              {CATEGORIES.map((c) => (
                <button
                  key={c.id || 'all'}
                  type="button"
                  className={`dar-chip${category === c.id ? ' dar-chip--active' : ''}`}
                  aria-pressed={category === c.id}
                  onClick={() => setCategory(c.id)}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <Button variant="secondary" onClick={() => void loadForms()}>
              Обновить список
            </Button>
            {capabilities && !capabilities.generation_ready ? (
              <div className="dar-callout dar-callout--warning" role="status">
                <Alert title="Заполнение ограничено" tone="warning">
                  {(capabilities.reasons && capabilities.reasons[0]) ||
                    capabilities.font_reason ||
                    'Нет шаблона, готового к заполнению.'}
                  {capabilities.official_templates_count === 0
                    ? ' Государственные бланки появятся после проверки официального источника.'
                    : ''}
                </Alert>
              </div>
            ) : null}
            {loadError ? (
              <div className="dar-callout dar-callout--danger" role="alert">
                <p>{loadError}</p>
                <Button variant="secondary" onClick={() => void loadForms()}>
                  Повторить
                </Button>
              </div>
            ) : null}
            {loading ? (
              <ul className="dar-template-grid" aria-label="Загрузка шаблонов">
                {Array.from({ length: 6 }).map((_, i) => (
                  <li key={i}>
                    <TemplateCardSkeleton />
                  </li>
                ))}
              </ul>
            ) : loadError ? null : filtered.length === 0 ? (
              <EmptyState
                title="Шаблоны не найдены"
                description="Измените поиск или категорию. Если каталог пуст — попробуйте позже."
                action={
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSearch('');
                      setCategory('');
                    }}
                  >
                    Сбросить фильтры
                  </Button>
                }
              />
            ) : (
              <ul className="dar-template-grid">
                {filtered.map((form) => (
                  <li key={form.id}>
                    <TemplateCard
                      title={form.title}
                      purpose={form.warning || form.category_label}
                      organ={form.organ}
                      reviewedAt={form.edition || 'дата уточняется'}
                      status={formatStatus(form.status)}
                      statusTone={statusTone(form.status, form.fill_ready)}
                      category={form.category}
                      categoryLabel={form.category_label}
                      action={
                        form.fill_ready &&
                        !form.unavailable_reason &&
                        capabilities?.generation_ready ? (
                          <Link href={`/app/forms/${form.id}`} className="dar-btn dar-btn--primary">
                            Заполнить
                          </Link>
                        ) : form.worksheet_ready && capabilities?.font_ready !== false ? (
                          <>
                            <Link
                              href={`/app/forms/${form.id}`}
                              className="dar-btn dar-btn--primary"
                            >
                              Подготовить сведения
                            </Link>
                            <p className="dar-muted">
                              {form.unavailable_reason ||
                                'Соберите сведения и сверьте их с документами.'}
                            </p>
                            {form.official_url ? (
                              <a
                                href={form.official_url}
                                className="dar-link"
                                target="_blank"
                                rel="noreferrer"
                              >
                                Официальный источник
                              </a>
                            ) : null}
                          </>
                        ) : (
                          <>
                            <span className="dar-badge dar-badge--warning">
                              Заполнение недоступно
                            </span>
                            {form.unavailable_reason ? (
                              <p className="dar-muted">{form.unavailable_reason}</p>
                            ) : null}
                            <Link
                              href="/app/generator?tab=wizard"
                              className="dar-btn dar-btn--secondary"
                            >
                              Чеклист в мастере
                            </Link>
                          </>
                        )
                      }
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        }
      />
    </div>
  );
}

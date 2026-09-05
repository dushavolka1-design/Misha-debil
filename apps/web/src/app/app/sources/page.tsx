import { Badge, ScreenStateView, SourceCitation, parseScreenState } from '@dar/ui';

import { formatSourceState } from '../../../lib/statusLabels';
import { getApiBase } from '../../../lib/apiBase';

export default async function SourcesPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const state = parseScreenState((await searchParams).state);

  let sources: Array<{
    id: string;
    title: string;
    organ: string;
    official_url: string;
    state: string;
    host: string;
  }> = [];
  let fetchFailed = false;

  try {
    const res = await fetch(`${getApiBase()}/sources`, { next: { revalidate: 0 } });
    if (res.ok) {
      sources = await res.json();
    } else {
      fetchFailed = true;
    }
  } catch {
    fetchFailed = true;
    sources = [];
  }

  return (
    <div>
      <h1 className="dar-page-title">Источники норм и форм</h1>
      <p className="dar-page-lead">
        Справочник официальных публикаций, на которых основаны шаблоны и проверки. Нормы не подставляются «из памяти
        модели».
      </p>
      {fetchFailed ? (
        <div className="dar-panel" role="alert">
          <p style={{ margin: 0 }}>Не удалось загрузить реестр источников. Проверьте подключение к серверу.</p>
        </div>
      ) : null}
      <ScreenStateView
        state={state}
        emptyTitle="Источники пока не добавлены"
        emptyDescription="Реестр заполняется при настройке сервиса."
        ready={
          <div className="dar-stack">
            <div className="dar-panel">
              <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Как мы ссылаемся на источник</h2>
              <SourceCitation
                title="Официальный портал правовой информации"
                version="Подтверждённая редакция"
                snapshotId="пример"
              />
              <p style={{ marginBottom: 0, color: 'var(--dar-color-text-muted)', fontSize: 'var(--dar-text-sm)' }}>
                Орган, документ, номер и дата, цитата, ссылка и статус проверки — в карточке каждого шаблона и отчёта.
              </p>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 12 }}>
              {sources.map((s) => (
                <li key={s.id} className="dar-panel">
                  <div className="dar-row" style={{ justifyContent: 'space-between' }}>
                    <strong>{s.title}</strong>
                    <Badge tone={s.state === 'approved' ? 'success' : 'warning'}>{formatSourceState(s.state)}</Badge>
                  </div>
                  <p style={{ marginBottom: 4 }}>{s.organ}</p>
                  <p style={{ marginBottom: 0 }}>
                    <a href={s.official_url} rel="noreferrer" target="_blank">
                      {s.host}
                    </a>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        }
      />
    </div>
  );
}

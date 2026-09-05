import { ScreenStateView, parseScreenState } from '@dar/ui';

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const state = parseScreenState((await searchParams).state);

  return (
    <div>
      <h1 className="dar-page-title">Сравнение документов</h1>
      <p className="dar-page-lead">
        Diff по сторонам, иерархии разделов и смысловым пунктам (добавлено / удалено / изменено) с двумя ссылками на
        источник. Без оценки «какой выгоднее». Данные другого пользователя не подмешиваются.
      </p>
      <ScreenStateView
        state={state}
        emptyTitle="Выберите документы"
        emptyDescription="Нужно минимум два документа вашего аккаунта в состоянии «Готов»."
        ready={
          <div className="dar-panel">
            <p style={{ margin: 0, color: 'var(--dar-color-text-secondary)' }}>
              Загрузите и проанализируйте документы в разделе «Анализатор», затем вернитесь к сравнению.
            </p>
          </div>
        }
      />
    </div>
  );
}

import Link from 'next/link';

import { ScreenStateView, parseScreenState } from '@dar/ui';

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const { state: raw } = await searchParams;
  const state = parseScreenState(raw);

  return (
    <div>
      <h1 className="dar-page-title">Обзор</h1>
      <p className="dar-page-lead">
        Перейдите в раздел «Анализатор» для загрузки и просмотра документов.
      </p>
      <ScreenStateView
        state={state}
        emptyTitle="Документов пока нет"
        emptyDescription="Загрузите первый файл, чтобы увидеть историю здесь."
        ready={
          <div className="dar-stack">
            <Link className="dar-btn dar-btn--primary" href="/app/analyzer?tab=documents">
              Мои документы
            </Link>
            <Link className="dar-btn dar-btn--secondary" href="/app/analyzer?tab=new">
              Новый анализ
            </Link>
          </div>
        }
      />
    </div>
  );
}

import type { ReactNode } from 'react';

import { Alert } from './Feedback';
import { Button } from './Button';
import { EmptyState } from './Domain';
import { Skeleton } from './Feedback';

export type ScreenState =
  'ready' | 'loading' | 'empty' | 'error' | 'forbidden' | 'expired' | 'offline';

export function ScreenStateView({
  state,
  ready,
  emptyTitle = 'Пока пусто',
  emptyDescription = 'Здесь появятся данные, когда вы начнёте работу.',
  emptyAction,
  onRetry,
}: {
  state: ScreenState;
  ready: ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  onRetry?: () => void;
}) {
  if (state === 'loading') {
    return (
      <div className="dar-stack" aria-busy="true" aria-live="polite">
        <Skeleton height={28} width="40%" label="Загрузка заголовка" />
        <Skeleton height={120} label="Загрузка содержимого" />
        <Skeleton height={120} label="Загрузка содержимого" />
      </div>
    );
  }
  if (state === 'empty') {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />;
  }
  if (state === 'error') {
    return (
      <Alert title="Не удалось загрузить данные" tone="danger">
        <p>Попробуйте ещё раз. Если ошибка повторяется — обратитесь в поддержку.</p>
        {onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            Повторить
          </Button>
        ) : null}
      </Alert>
    );
  }
  if (state === 'forbidden') {
    return (
      <Alert title="Недостаточно прав" tone="warning">
        У вашей роли нет доступа к этому разделу.
      </Alert>
    );
  }
  if (state === 'expired') {
    return (
      <Alert title="Сессия или ссылка устарела" tone="warning">
        Войдите снова или запросите новую ссылку.
      </Alert>
    );
  }
  if (state === 'offline') {
    return (
      <Alert title="Нет сети" tone="info">
        <p>Проверьте подключение и повторите попытку.</p>
        {onRetry ? (
          <Button variant="secondary" onClick={onRetry}>
            Повторить
          </Button>
        ) : null}
      </Alert>
    );
  }
  return <>{ready}</>;
}

export function parseScreenState(value: string | null | undefined): ScreenState {
  const allowed: ScreenState[] = [
    'ready',
    'loading',
    'empty',
    'error',
    'forbidden',
    'expired',
    'offline',
  ];
  if (value && (allowed as string[]).includes(value)) return value as ScreenState;
  return 'ready';
}

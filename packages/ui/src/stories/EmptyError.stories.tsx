import type { Meta, StoryObj } from '@storybook/react';

import { Button } from '../Button';
import { EmptyState } from '../Domain';
import { ScreenStateView } from '../ScreenState';

const meta: Meta = {
  title: 'DAR/Empty Error states',
};
export default meta;

export const Empty: StoryObj = {
  render: () => (
    <EmptyState
      title="Шаблоны не найдены"
      description="Измените поиск или категорию. Если каталог пуст — попробуйте позже."
      action={<Button variant="secondary">Сбросить фильтры</Button>}
    />
  ),
};

export const ErrorState: StoryObj = {
  render: () => <ScreenStateView state="error" ready={null} onRetry={() => undefined} />,
};

export const Offline: StoryObj = {
  render: () => <ScreenStateView state="offline" ready={null} onRetry={() => undefined} />,
};

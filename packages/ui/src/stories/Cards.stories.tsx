import type { Meta, StoryObj } from '@storybook/react';

import { Alert, Badge } from '../Feedback';

const meta: Meta = {
  title: 'DAR/Cards',
};
export default meta;

export const Hierarchy: StoryObj = {
  render: () => (
    <div className="dar-stack">
      <section className="dar-card dar-card--hero">
        <h2>Hero surface</h2>
        <p>Главная рабочая область — загрузка или ключевое действие.</p>
      </section>
      <article className="dar-card">
        <h3>Карточка</h3>
        <p>Обычная поверхность с тенью и границей #CBD5E1.</p>
      </article>
      <div className="dar-card dar-card--inset">
        <strong>Inset panel</strong>
        <p>Вложенный блок без отдельной «белой коробки».</p>
      </div>
      <div className="dar-callout dar-callout--warning">
        <Badge tone="warning">Внимание</Badge>
        <p>Тонированный callout для ограничений сервиса.</p>
      </div>
      <Alert title="Успех" tone="success">
        Состояние success.
      </Alert>
    </div>
  ),
};

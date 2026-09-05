import type { Meta, StoryObj } from '@storybook/react';

const meta: Meta = {
  title: 'DAR/Typography',
};
export default meta;

export const Scale: StoryObj = {
  render: () => (
    <div className="dar-stack">
      <h1>Заголовок первого уровня</h1>
      <h2>Заголовок раздела</h2>
      <h3>Подзаголовок карточки</h3>
      <p>
        Основной текст 16 px, вес 500, межстрочный интервал 1.55. Кириллица Onest: договор, уведомление,
        пребывание.
      </p>
      <p className="dar-muted">Вторичный текст не светлее #475569 и не меньше 14 px.</p>
      <label className="dar-field__label">Подпись поля и кнопка — 14–16 px, вес 600</label>
      <details>
        <summary>Технические подробности</summary>
        <p className="dar-mono">id: 7f3a91c2</p>
      </details>
    </div>
  ),
};

import type { Meta, StoryObj } from '@storybook/react';

import { Button } from '../Button';
import { TemplateCard, TemplateCardSkeleton } from '../TemplateCard';

const meta: Meta = {
  title: 'DAR/TemplateCard',
};
export default meta;

export const Catalog: StoryObj = {
  render: () => (
    <ul className="dar-template-grid">
      <li>
        <TemplateCard
          title="Медицинская памятка сервиса"
          purpose="Информационный лист для подготовки к приёму"
          organ="Docly"
          reviewedAt="25.08.2026"
          status="Готово к заполнению"
          statusTone="success"
          category="medical"
          categoryLabel="Медицинские памятки"
          action={<Button>Заполнить</Button>}
        />
      </li>
      <li>
        <TemplateCardSkeleton />
      </li>
    </ul>
  ),
};

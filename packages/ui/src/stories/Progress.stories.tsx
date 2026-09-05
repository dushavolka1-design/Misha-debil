import type { Meta, StoryObj } from '@storybook/react';

import { Progress } from '../Feedback';
import { Timeline } from '../Domain';

const meta: Meta = {
  title: 'DAR/Progress',
};
export default meta;

export const BarAndTimeline: StoryObj = {
  render: () => (
    <div className="dar-stack">
      <Progress value={62} label="Разбор текста" />
      <Timeline
        items={[
          { id: '1', title: 'Файл принят', time: '09:12' },
          { id: '2', title: 'Извлечение текста', detail: 'Страницы 1–4' },
          { id: '3', title: 'Сопоставление фактов' },
        ]}
      />
    </div>
  ),
};

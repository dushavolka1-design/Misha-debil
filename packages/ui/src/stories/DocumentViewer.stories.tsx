import type { Meta, StoryObj } from '@storybook/react';

import { DocumentViewer } from '../DocumentViewer';

const meta: Meta = {
  title: 'DAR/DocumentViewer',
};
export default meta;

export const Workspace: StoryObj = {
  render: () => (
    <DocumentViewer
      pageLabel="Страница 1 / 3"
      quote="Арендная плата вносится ежемесячно"
      highlight={{ left: '12%', top: '28%', width: '54%', height: '12%' }}
    >
      <p className="dar-doc-line">
        Арендная плата вносится ежемесячно не позднее пятого числа месяца, следующего за расчётным.
      </p>
    </DocumentViewer>
  ),
};

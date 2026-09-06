import type { Preview } from '@storybook/react';

import '../src/styles/index.css';

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i } },
    a11y: { test: 'todo' },
  },
};

export default preview;

import type { Meta, StoryObj } from '@storybook/react';

import { Button } from '../Button';

const meta: Meta = {
  title: 'DAR/Buttons',
};
export default meta;

export const States: StoryObj = {
  render: () => (
    <div className="dar-stack">
      <div className="dar-row">
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
      </div>
      <div className="dar-row">
        <Button size="sm">Small 44</Button>
        <Button size="lg">Large 48</Button>
        <Button loading>Загрузка</Button>
        <Button disabled>Disabled</Button>
      </div>
    </div>
  ),
};

import type { Meta, StoryObj } from '@storybook/react';

import { Button } from '../Button';
import { Alert, Badge, Progress, Skeleton } from '../Feedback';
import { ConfidenceIndicator, Disclaimer, FindingCard } from '../Domain';
import { Input } from '../FormControls';

import '../styles/index.css';

const meta: Meta = {
  title: 'DAR/Foundation',
};
export default meta;

export const Buttons: StoryObj = {
  render: () => (
    <div className="dar-row">
      <Button>Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Danger</Button>
    </div>
  ),
};

export const FormField: StoryObj = {
  render: () => (
    <div style={{ maxWidth: 360 }}>
      <Input id="story-email" label="Email" error="Укажите корректный email" />
    </div>
  ),
};

export const FindingAndConfidence: StoryObj = {
  render: () => (
    <div className="dar-stack" style={{ maxWidth: 420 }}>
      <FindingCard
        title="Арендная плата"
        kind="fact"
        value="120 000 RUB / месяц"
        uncertainty="Низкая уверенность извлечения"
      />
      <ConfidenceIndicator value={0.61} />
      <Badge tone="warning">Требует проверки</Badge>
      <Progress value={62} label="Анализ сущностей" />
      <Skeleton height={24} />
      <Alert title="Не юридическая экспертиза" tone="warning">
        Уверенность — только про извлечение/сопоставление.
      </Alert>
      <Disclaimer />
    </div>
  ),
};

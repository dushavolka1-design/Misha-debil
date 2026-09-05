import type { Meta, StoryObj } from '@storybook/react';

const TOKENS = [
  ['Page', '#F4F7FB', 'var(--dar-color-bg)'],
  ['Surface', '#FFFFFF', 'var(--dar-color-bg-elevated)'],
  ['Ink', '#111827', 'var(--dar-color-text)'],
  ['Secondary', '#334155', 'var(--dar-color-text-secondary)'],
  ['Muted', '#475569', 'var(--dar-color-text-muted)'],
  ['Accent', '#4F3CC9', 'var(--dar-color-accent)'],
  ['Success', '#0F766E', 'var(--dar-color-success)'],
  ['Warning', '#B45309', 'var(--dar-color-warning)'],
  ['Danger', '#B42318', 'var(--dar-color-danger)'],
  ['Info', '#1D4ED8', 'var(--dar-color-info)'],
  ['Border', '#CBD5E1', 'var(--dar-color-border)'],
];

const meta: Meta = {
  title: 'DAR/Colors',
};
export default meta;

export const Palette: StoryObj = {
  render: () => (
    <div className="dar-metrics">
      {TOKENS.map(([name, hex, token]) => (
        <div key={name} className="dar-metric">
          <span
            className="dar-skeleton"
            style={{ height: 48, background: token, animation: 'none' }}
            aria-hidden="true"
          />
          <strong>{name}</strong>
          <span className="dar-metric__label">{hex}</span>
        </div>
      ))}
    </div>
  ),
};

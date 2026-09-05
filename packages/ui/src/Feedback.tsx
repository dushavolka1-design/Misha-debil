'use client';

import type { ReactNode } from 'react';
import { useId, useState } from 'react';

export function Tabs({
  items,
  defaultValue,
  onChange,
}: {
  items: Array<{ value: string; label: string; panel: ReactNode }>;
  defaultValue?: string;
  onChange?: (value: string) => void;
}) {
  const baseId = useId();
  const [value, setValue] = useState(defaultValue ?? items[0]?.value ?? '');
  const active = items.find((i) => i.value === value) ?? items[0];

  return (
    <div>
      <div className="dar-tabs" role="tablist" aria-label="Разделы">
        {items.map((item) => {
          const selected = item.value === active?.value;
          return (
            <button
              key={item.value}
              id={`${baseId}-tab-${item.value}`}
              className="dar-tabs__tab"
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.value}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => {
                setValue(item.value);
                onChange?.(item.value);
              }}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {active ? (
        <div
          id={`${baseId}-panel-${active.value}`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${active.value}`}
          className="dar-tabs__panel"
        >
          {active.panel}
        </div>
      ) : null}
    </div>
  );
}

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span
      className="dar-tooltip"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span tabIndex={0} aria-describedby={open ? id : undefined}>
        {children}
      </span>
      {open ? (
        <span className="dar-tooltip__bubble" role="tooltip" id={id}>
          {label}
        </span>
      ) : null}
    </span>
  );
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode;
  tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';
}) {
  return <span className={`dar-badge dar-badge--${tone}`}>{children}</span>;
}

export function Alert({
  title,
  children,
  tone = 'info',
}: {
  title: string;
  children?: ReactNode;
  tone?: 'info' | 'success' | 'warning' | 'danger';
}) {
  return (
    <div className={`dar-alert dar-alert--${tone}`} role="status">
      <strong>{title}</strong>
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function Progress({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="dar-progress-block">
      <div className="dar-progress-block__head">
        <span>{label}</span>
        <span aria-hidden="true">{clamped}%</span>
      </div>
      <div
        className="dar-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-label={label}
      >
        <div className="dar-progress__bar" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

export function Skeleton({
  width = '100%',
  height = 16,
  label = 'Загрузка',
}: {
  width?: string | number;
  height?: string | number;
  label?: string;
}) {
  return (
    <span
      className="dar-skeleton"
      style={{ width, height }}
      role="status"
      aria-label={label}
    />
  );
}

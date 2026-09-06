'use client';

import type { ReactNode } from 'react';
import { useId } from 'react';

export type SectionTabItem = {
  value: string;
  label: string;
  panel: ReactNode;
};

export function UrlSectionTabs({
  items,
  value,
  onChange,
  ariaLabel,
}: {
  items: SectionTabItem[];
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
}) {
  const baseId = useId();
  const active = items.find((i) => i.value === value) ?? items[0];

  return (
    <div className="dar-section-tabs">
      <div className="dar-segmented" role="tablist" aria-label={ariaLabel}>
        {items.map((item) => {
          const selected = item.value === active?.value;
          return (
            <button
              key={item.value}
              id={`${baseId}-tab-${item.value}`}
              type="button"
              role="tab"
              className="dar-segmented__item"
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.value}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.value)}
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
          className="dar-section-tabs__panel"
        >
          {active.panel}
        </div>
      ) : null}
    </div>
  );
}

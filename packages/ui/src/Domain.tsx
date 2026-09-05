import type { ReactNode } from 'react';

import { FileSearch } from 'lucide-react';

import { Icon } from './Icon';

export function SourceCitation({
  title,
  version,
  snapshotId,
  href,
}: {
  title: string;
  version: string;
  snapshotId: string;
  href?: string;
}) {
  return (
    <aside className="dar-citation" aria-label="Ссылка на снимок источника">
      <strong>{title}</strong>
      <span>
        Версия {version} · снимок <span className="dar-mono">{snapshotId}</span>
      </span>
      {href ? (
        <a href={href} rel="noreferrer">
          Открыть снимок источника
        </a>
      ) : null}
    </aside>
  );
}

export type FindingKind = 'fact' | 'inference';

export function FindingCard({
  title,
  kind,
  value,
  uncertainty,
  active,
  onSelect,
}: {
  title: string;
  kind: FindingKind;
  value: string;
  uncertainty?: string | undefined;
  active?: boolean | undefined;
  onSelect?: (() => void) | undefined;
}) {
  return (
    <button
      type="button"
      className="dar-finding"
      data-active={active ? 'true' : 'false'}
      onClick={onSelect}
      aria-pressed={active}
    >
      <div className="dar-finding__head">
        <strong>{title}</strong>
        <span className={`dar-badge dar-badge--${kind === 'fact' ? 'info' : 'accent'}`}>
          {kind === 'fact' ? 'Факт' : 'Вывод'}
        </span>
      </div>
      <p className="dar-finding__value">{value}</p>
      {uncertainty ? <p className="dar-finding__meta">{uncertainty}</p> : null}
    </button>
  );
}

/** Extraction/matching confidence — NEVER legal reliability. */
export function ConfidenceIndicator({
  value,
  label = 'Уверенность извлечения/сопоставления',
}: {
  value: number;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);
  return (
    <div className="dar-confidence" aria-label={`${label}: ${pct}%`}>
      <span>
        {label}: {pct}%
      </span>
      <div className="dar-confidence__meter" aria-hidden="true">
        <div className="dar-confidence__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="dar-confidence__note">
        Не является оценкой юридической надёжности или верности нормы.
      </span>
    </div>
  );
}

export function Timeline({
  items,
}: {
  items: Array<{ id: string; title: string; detail?: string; time?: string }>;
}) {
  return (
    <ol className="dar-timeline" aria-label="Хронология">
      {items.map((item) => (
        <li key={item.id} className="dar-timeline__item">
          <span className="dar-timeline__dot" aria-hidden="true" />
          <div>
            <strong>{item.title}</strong>
            {item.time ? <div className="dar-timeline__time">{item.time}</div> : null}
            {item.detail ? <p className="dar-timeline__detail">{item.detail}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="dar-empty" role="status">
      <span className="dar-empty__icon" aria-hidden="true">
        <Icon icon={FileSearch} size={26} />
      </span>
      <h2 className="dar-empty__title">{title}</h2>
      <p className="dar-empty__text">{description}</p>
      {action}
    </div>
  );
}

export function Disclaimer({
  dense,
}: {
  dense?: boolean;
} = {}) {
  return (
    <aside className={`dar-disclaimer${dense ? ' dar-disclaimer--dense' : ''}`} role="note">
      <strong>Важно.</strong> «Docly» — частный информационный помощник. Сервис не оказывает
      юридическую или медицинскую экспертизу, не является государственным органом и не заменяет
      консультацию специалиста. Этот disclaimer не ограничивает обязательные права потребителя и не
      снимает ответственность, предусмотренную законом.
    </aside>
  );
}

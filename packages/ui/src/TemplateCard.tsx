import type { ReactNode } from 'react';

export type TemplateCardStatusTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';
export type TemplateCategory = 'entry_stay' | 'work' | 'rvp_vnz' | 'medical' | string;

export function TemplateCard({
  title,
  purpose,
  organ,
  reviewedAt,
  status,
  statusTone = 'info',
  category,
  categoryLabel,
  action,
}: {
  title: string;
  purpose: string;
  organ: string;
  reviewedAt: string;
  status: string;
  statusTone?: TemplateCardStatusTone;
  category: TemplateCategory;
  categoryLabel: string;
  action: ReactNode;
}) {
  return (
    <article className="dar-template-card">
      <span className={`dar-template-card__cat dar-template-card__cat--${category}`}>{categoryLabel}</span>
      <h3 className="dar-template-card__title">{title}</h3>
      <p className="dar-template-card__meta">{purpose}</p>
      <p className="dar-template-card__meta">Орган: {organ}</p>
      <p className="dar-template-card__meta">Проверено: {reviewedAt}</p>
      <span className={`dar-badge dar-badge--${statusTone}`}>{status}</span>
      <div className="dar-template-card__actions">{action}</div>
    </article>
  );
}

export function TemplateCardSkeleton() {
  return (
    <div className="dar-skeleton-card" aria-hidden="true">
      <span className="dar-skeleton" style={{ width: 120, height: 28 }} />
      <span className="dar-skeleton" style={{ width: '80%', height: 22 }} />
      <span className="dar-skeleton" style={{ width: '100%', height: 16 }} />
      <span className="dar-skeleton" style={{ width: '60%', height: 16 }} />
      <span className="dar-skeleton" style={{ width: 140, height: 44 }} />
    </div>
  );
}

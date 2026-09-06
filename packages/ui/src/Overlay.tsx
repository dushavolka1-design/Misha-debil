'use client';

import type { ReactNode } from 'react';
import { useEffect, useId, useRef } from 'react';

import { Button } from './Button';

export function Dialog({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="dar-dialog-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        className="dar-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={ref}
      >
        <div className="dar-dialog__head">
          <h2 id={titleId} className="dar-dialog__title">
            {title}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Закрыть диалог">
            Закрыть
          </Button>
        </div>
        {children}
      </div>
    </>
  );
}

export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const titleId = useId();
  if (!open) return null;
  return (
    <>
      <div className="dar-drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="dar-drawer" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="dar-drawer__head">
          <h2 id={titleId} className="dar-drawer__title">
            {title}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Закрыть панель">
            Закрыть
          </Button>
        </div>
        {children}
      </aside>
    </>
  );
}

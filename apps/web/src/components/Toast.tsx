'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type ToastTone = 'success' | 'info' | 'danger';

type ToastState = {
  message: string;
  tone: ToastTone;
} | null;

type ToastApi = {
  showSuccess: (message: string) => void;
  showInfo: (message: string) => void;
  showError: (message: string) => void;
  clear: () => void;
};

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState>(null);

  const show = useCallback((message: string, tone: ToastTone) => {
    setToast({ message, tone });
    window.setTimeout(() => setToast((cur) => (cur?.message === message ? null : cur)), 4000);
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      showSuccess: (message) => show(message, 'success'),
      showInfo: (message) => show(message, 'info'),
      showError: (message) => show(message, 'danger'),
      clear: () => setToast(null),
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      {toast ? (
        <div
          className={`dar-toast dar-toast--${toast.tone}`}
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {toast.message}
        </div>
      ) : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast requires ToastProvider');
  }
  return ctx;
}

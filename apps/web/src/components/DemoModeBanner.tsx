'use client';

import { useEffect, useState } from 'react';

import { Alert } from '@dar/ui';

import { apiFetch } from '../lib/apiClient';

type PublicConfig = { demo_mode: boolean };

export function DemoModeBanner() {
  const [demo, setDemo] = useState(
    () => process.env.NEXT_PUBLIC_DEMO_MODE === 'true',
  );

  useEffect(() => {
    void apiFetch<PublicConfig>('/config/public', { retries: 0, timeoutMs: 4000 })
      .then((cfg) => setDemo(cfg.demo_mode))
      .catch(() => undefined);
  }, []);

  if (!demo) return null;

  return (
    <Alert title="Демонстрационный режим" tone="warning">
      Результаты могут использовать тестовые OCR/LLM-провайдеры. Не используйте как юридическое заключение.
    </Alert>
  );
}

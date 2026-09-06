'use client';

import Link from 'next/link';
import { useCallback, useState } from 'react';

import { Button } from '@dar/ui';

export function ServiceUnavailable({
  title = 'Сервис анализа не запущен',
  description = 'Не удалось связаться с API. Запустите Docly с ярлыка и нажмите «Повторить».',
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const retry = useCallback(async () => {
    if (!onRetry) {
      window.location.reload();
      return;
    }
    setBusy(true);
    try {
      await onRetry();
    } finally {
      setBusy(false);
    }
  }, [onRetry]);

  return (
    <div className="dar-empty" role="alert">
      <h2 className="dar-empty__title">{title}</h2>
      <p className="dar-empty__text">{description}</p>
      <div className="dar-row">
        <Button onClick={() => void retry()} disabled={busy}>
          Повторить
        </Button>
        <Link href="/" className="dar-btn dar-btn--ghost">
          На главную
        </Link>
      </div>
    </div>
  );
}

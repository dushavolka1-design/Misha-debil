'use client';

import { Button, Dialog } from '@dar/ui';
import { useState } from 'react';

import { ApiError, deleteDocument } from '../lib/apiClient';

const DERIVED_ITEMS = [
  'оригинальный файл в хранилище',
  'нормализованные и производные артефакты',
  'извлечённый текст и отчёты анализа',
  'ключи шифрования (DEK) для этого документа',
  'записи прогресса и результатов анализа',
];

type Props = {
  documentId: string;
  displayName: string;
  open: boolean;
  onClose: () => void;
  onDeleted: () => void;
};

export function DeleteDocumentDialog({ documentId, displayName, open, onClose, onDeleted }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await deleteDocument(documentId);
      setDone(true);
      onDeleted();
    } catch (err) {
      setError(
        err instanceof ApiError ? (err.detail ?? err.message) : 'Не удалось удалить документ',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} title="Удалить документ?" onClose={onClose}>
      {done ? (
        <p role="status">Документ «{displayName}» и связанные данные помечены к удалению.</p>
      ) : (
        <>
          <p>
            Будут удалены производные данные для <strong>{displayName}</strong>:
          </p>
          <ul>
            {DERIVED_ITEMS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p style={{ color: 'var(--dar-color-text-secondary)', fontSize: 'var(--dar-text-sm)' }}>
            Операция необратима. Юридически значимые копии вне сервиса не затрагиваются.
          </p>
          {error ? (
            <p role="alert" style={{ color: 'var(--dar-color-danger)' }}>
              {error}
            </p>
          ) : null}
          <div className="dar-row">
            <Button variant="danger" disabled={busy} onClick={() => void confirm()}>
              {busy ? 'Удаление…' : 'Удалить навсегда'}
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Отмена
            </Button>
          </div>
        </>
      )}
    </Dialog>
  );
}

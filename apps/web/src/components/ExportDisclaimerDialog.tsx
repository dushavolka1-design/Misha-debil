'use client';

import { Button, Dialog } from '@dar/ui';

export const EXPORT_DISCLAIMER_BODY =
  'Экспортированный файл — информационная справка по загруженному документу. ' +
  'Он не является юридическим заключением, медицинским документом или официальным ответом госоргана. ' +
  'Перед принятием решений проверьте данные по оригиналу и при необходимости обратитесь к специалисту. ' +
  'Ответственность за использование материала несёт пользователь.';

type Props = {
  open: boolean;
  formatLabel: string;
  onConfirm: () => void;
  onClose: () => void;
};

export function ExportDisclaimerDialog({ open, formatLabel, onConfirm, onClose }: Props) {
  return (
    <Dialog open={open} title={`Экспорт ${formatLabel}`} onClose={onClose}>
      <p>{EXPORT_DISCLAIMER_BODY}</p>
      <div className="dar-row">
        <Button onClick={onConfirm}>Понятно, скачать</Button>
        <Button variant="ghost" onClick={onClose}>
          Отмена
        </Button>
      </div>
    </Dialog>
  );
}

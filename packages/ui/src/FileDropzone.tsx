'use client';

import { FileUp, LoaderCircle, CircleAlert, FileCheck } from 'lucide-react';
import { useId, useState } from 'react';

import { Icon } from './Icon';

export type UploadZoneStatus = 'idle' | 'drag' | 'selected' | 'scanning' | 'error';

export function FileDropzone({
  label = 'Перетащите файл сюда или выберите на устройстве',
  accept = '.pdf,.docx,.jpg,.jpeg,.png',
  onFiles,
  disabled,
  status,
  fileName,
  errorText,
}: {
  label?: string;
  accept?: string;
  onFiles?: (files: FileList) => void;
  disabled?: boolean;
  status?: UploadZoneStatus;
  fileName?: string | null;
  errorText?: string | null;
}) {
  const inputId = useId();
  const [active, setActive] = useState(false);
  const [pickedName, setPickedName] = useState<string | null>(null);
  const resolvedName = fileName ?? pickedName;
  const resolvedStatus: UploadZoneStatus =
    status ?? (active ? 'drag' : resolvedName ? 'selected' : 'idle');

  const icon =
    resolvedStatus === 'error'
      ? CircleAlert
      : resolvedStatus === 'scanning'
        ? LoaderCircle
        : resolvedStatus === 'selected'
          ? FileCheck
          : FileUp;

  return (
    <div
      className="dar-dropzone"
      data-active={active}
      data-status={resolvedStatus}
      onDragEnter={(e) => {
        e.preventDefault();
        if (!disabled) setActive(true);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => setActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setActive(false);
        if (disabled || !e.dataTransfer.files?.length) return;
        setPickedName(e.dataTransfer.files[0]?.name ?? null);
        onFiles?.(e.dataTransfer.files);
      }}
      role="region"
      aria-label="Область загрузки файла"
    >
      <span className="dar-dropzone__icon" aria-hidden="true">
        <Icon icon={icon} size={26} />
      </span>
      <p className="dar-dropzone__title">{label}</p>
      <p className="dar-dropzone__hint">
        PDF, DOCX, JPEG, PNG. Частный информационный сервис — не государственный портал.
      </p>
      {resolvedName ? (
        <p className="dar-dropzone__hint" aria-live="polite">
          Выбрано: {resolvedName}
        </p>
      ) : null}
      {errorText ? (
        <p className="dar-field__error" role="alert">
          {errorText}
        </p>
      ) : null}
      <input
        id={inputId}
        type="file"
        accept={accept}
        disabled={disabled}
        className="dar-sr-only"
        onChange={(e) => {
          if (e.target.files?.length) {
            setPickedName(e.target.files[0]?.name ?? null);
            onFiles?.(e.target.files);
          }
        }}
      />
      <label htmlFor={inputId}>
        <span className="dar-btn dar-btn--secondary" role="button" aria-disabled={disabled}>
          Выбрать файл
        </span>
      </label>
    </div>
  );
}

export { FileDropzone as UploadZone };

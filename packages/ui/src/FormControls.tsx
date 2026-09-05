import type { InputHTMLAttributes, ReactNode } from 'react';

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string | undefined;
  error?: string | undefined;
  id: string;
  leading?: ReactNode;
};

export function Input({ label, hint, error, id, className = '', leading, ...props }: InputProps) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="dar-field">
      <label className="dar-field__label" htmlFor={id}>
        {label}
      </label>
      {leading ? (
        <div className="dar-input-wrap">
          <span className="dar-input-wrap__icon" aria-hidden="true">
            {leading}
          </span>
          <input
            id={id}
            className={`dar-input ${className}`.trim()}
            aria-invalid={Boolean(error) || undefined}
            aria-describedby={describedBy || undefined}
            {...props}
          />
        </div>
      ) : (
        <input
          id={id}
          className={`dar-input ${className}`.trim()}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedBy || undefined}
          {...props}
        />
      )}
      {hint ? (
        <p className="dar-field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="dar-field__error" id={`${id}-error`} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function FormErrorSummary({
  title = 'Исправьте ошибки в форме',
  errors,
}: {
  title?: string;
  errors: Array<{ id: string; message: string }>;
}) {
  if (!errors.length) return null;
  return (
    <div className="dar-form-summary" role="alert" aria-live="polite">
      <strong>{title}</strong>
      <ul>
        {errors.map((e) => (
          <li key={e.id}>
            <a href={`#${e.id}`}>{e.message}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export type SelectProps = {
  id: string;
  label: string;
  options: Array<{ value: string; label: string }>;
  value?: string;
  onChange?: (value: string) => void;
  error?: string | undefined;
  hint?: string | undefined;
  disabled?: boolean;
  required?: boolean;
  name?: string;
};

export function Select({
  id,
  label,
  options,
  value,
  onChange,
  error,
  hint,
  disabled,
  required,
  name,
}: SelectProps) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(' ');
  return (
    <div className="dar-field">
      <label className="dar-field__label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        name={name}
        className="dar-select"
        value={value}
        disabled={disabled}
        required={required}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={describedBy || undefined}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {hint ? (
        <p className="dar-field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="dar-field__error" id={`${id}-error`} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function Checkbox({
  id,
  label,
  checked,
  onChange,
  disabled,
}: {
  id: string;
  label: ReactNode;
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="dar-check" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}

export function Radio({
  id,
  name,
  label,
  value,
  checked,
  onChange,
  disabled,
}: {
  id: string;
  name: string;
  label: ReactNode;
  value: string;
  checked?: boolean;
  onChange?: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="dar-radio" htmlFor={id}>
      <input
        id={id}
        type="radio"
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        onChange={() => onChange?.(value)}
      />
      <span>{label}</span>
    </label>
  );
}

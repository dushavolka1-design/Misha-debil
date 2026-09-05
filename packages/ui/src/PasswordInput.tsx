'use client';

import { useState, type InputHTMLAttributes } from 'react';
export type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  id: string; label: string; hint?: string | undefined; error?: string | undefined;
  showLabel?: string; hideLabel?: string; capsLockLabel?: string;
};
export function PasswordInput({ id, label, hint, error, showLabel = 'Показать', hideLabel = 'Скрыть', capsLockLabel = 'Включён Caps Lock', className, onKeyDown, onKeyUp, onBlur, 'aria-describedby': externalDescription, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const describedBy = [externalDescription, hint && `${id}-hint`, error && `${id}-error`, capsLock && `${id}-caps`].filter(Boolean).join(' ');
  return <div className="dar-field docly-password">
    <label className="dar-field__label" htmlFor={id}>{label}</label>
    <div className="docly-password__control">
      <input {...props} id={id} type={visible ? 'text' : 'password'} className={['dar-input', className].filter(Boolean).join(' ')} aria-invalid={Boolean(error) || undefined} aria-describedby={describedBy || undefined}
        onKeyDown={(event) => { setCapsLock(event.getModifierState('CapsLock')); onKeyDown?.(event); }}
        onKeyUp={(event) => { setCapsLock(event.getModifierState('CapsLock')); onKeyUp?.(event); }}
        onBlur={(event) => { setCapsLock(false); onBlur?.(event); }} />
      <button type="button" className="docly-password__toggle" aria-controls={id} aria-pressed={visible} disabled={props.disabled} onClick={() => setVisible(!visible)}>{visible ? hideLabel : showLabel}</button>
    </div>
    {hint ? <p id={`${id}-hint`} className="dar-field__hint">{hint}</p> : null}
    {capsLock ? <p id={`${id}-caps`} role="status" className="dar-field__hint">{capsLockLabel}</p> : null}
    {error ? <p id={`${id}-error`} role="alert" className="dar-field__error">{error}</p> : null}
  </div>;
}

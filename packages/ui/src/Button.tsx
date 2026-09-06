import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className = '',
  type = 'button',
  disabled,
  children,
  ...props
}: ButtonProps) {
  const sizeClass = size === 'md' ? '' : ` dar-btn--${size}`;
  const loadingClass = loading ? ' dar-btn--loading' : '';
  return (
    <button
      type={type}
      className={`dar-btn dar-btn--${variant}${sizeClass}${loadingClass} ${className}`.trim()}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <span className="dar-btn__spinner" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

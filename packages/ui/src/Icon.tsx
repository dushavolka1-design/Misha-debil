import type { LucideIcon } from 'lucide-react';

export function Icon({
  icon: Glyph,
  size = 20,
  className = '',
  label,
}: {
  icon: LucideIcon;
  size?: number;
  className?: string;
  label?: string;
}) {
  return (
    <span className={`dar-icon ${className}`.trim()}>
      <Glyph size={size} strokeWidth={2} aria-hidden={label ? undefined : true} aria-label={label} />
    </span>
  );
}

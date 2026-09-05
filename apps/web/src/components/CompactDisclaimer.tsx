import Link from 'next/link';

export function CompactDisclaimer() {
  return (
    <p className="dar-disclaimer-compact" role="note">
      Информационный помощник, не государственная услуга и не замена консультации специалиста.{' '}
      <Link href="/app/profile">Подробнее об ограничениях</Link>
    </p>
  );
}

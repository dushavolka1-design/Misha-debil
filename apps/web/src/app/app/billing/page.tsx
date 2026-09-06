import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import BillingClient from './BillingClient';

export default function BillingPage() {
  return (
    <Suspense fallback={<Skeleton height={200} />}>
      <BillingClient />
    </Suspense>
  );
}

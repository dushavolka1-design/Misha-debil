import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import FormsCatalogClient from './FormsCatalogClient';

export default function FormsCatalogPage() {
  return (
    <Suspense fallback={<Skeleton height={240} />}>
      <FormsCatalogClient />
    </Suspense>
  );
}

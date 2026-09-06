import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import UploadClient from './UploadClient';

export default function UploadPage() {
  return (
    <Suspense fallback={<Skeleton height={200} />}>
      <UploadClient />
    </Suspense>
  );
}

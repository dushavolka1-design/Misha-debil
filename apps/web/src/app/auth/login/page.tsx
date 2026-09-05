import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import LoginClient from './LoginClient';

export default function LoginPage() {
  return (
    <Suspense fallback={<Skeleton height={200} />}>
      <LoginClient />
    </Suspense>
  );
}

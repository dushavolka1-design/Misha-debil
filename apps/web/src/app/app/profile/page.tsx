import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import ProfileClient from './ProfileClient';

export default function ProfilePage() {
  return (
    <Suspense fallback={<Skeleton height={240} />}>
      <ProfileClient />
    </Suspense>
  );
}

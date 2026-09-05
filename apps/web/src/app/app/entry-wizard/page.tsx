import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import EntryWizardClient from './EntryWizardClient';

export default function EntryWizardPage() {
  return (
    <Suspense fallback={<Skeleton height={240} />}>
      <EntryWizardClient />
    </Suspense>
  );
}

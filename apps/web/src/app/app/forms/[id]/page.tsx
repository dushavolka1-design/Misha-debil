import { Suspense } from 'react';

import { Skeleton } from '@dar/ui';

import FormFillClient from './FormFillClient';

export default async function FormFillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<Skeleton height={200} />}>
      <FormFillClient formId={id} />
    </Suspense>
  );
}

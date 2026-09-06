'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

import { Skeleton } from '@dar/ui';

import { buildAnalyzerDocumentUrl, fetchAnalysisRun } from '../../../../lib/apiClient';

export default function JobRedirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    void fetchAnalysisRun(params.id)
      .then((run) => {
        router.replace(buildAnalyzerDocumentUrl(run.document_id, run.id));
      })
      .catch(() => {
        router.replace(`/app/analyzer?tab=documents&run=${params.id}`);
      });
  }, [params.id, router]);

  return <Skeleton height={200} label="Переход к анализу" />;
}

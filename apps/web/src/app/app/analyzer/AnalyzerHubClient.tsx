'use client';

import { Suspense, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { Skeleton } from '@dar/ui';

import { UrlSectionTabs } from '../../../components/UrlSectionTabs';
import { OnboardingPanel } from '../../../components/OnboardingPanel';
import UploadClient from '../upload/UploadClient';
import ComparePanelClient from './ComparePanelClient';
import DocumentDetailView from './DocumentDetailView';
import DocumentsPanelClient from './DocumentsPanelClient';

const TAB_VALUES = ['new', 'documents', 'compare'] as const;
type TabValue = (typeof TAB_VALUES)[number];

function isTabValue(value: string | null): value is TabValue {
  return TAB_VALUES.includes(value as TabValue);
}

function AnalyzerHubInner() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const rawTab = searchParams.get('tab');
  const tab: TabValue = isTabValue(rawTab) ? rawTab : 'new';
  const documentId = searchParams.get('document');
  const runId = searchParams.get('run');
  const compareIds = searchParams.get('compare')?.split(',').filter(Boolean) ?? [];

  const replaceParams = useCallback(
    (mutate: (params: URLSearchParams) => void) => {
      const params = new URLSearchParams(searchParams.toString());
      mutate(params);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setTab = useCallback(
    (value: string) => {
      replaceParams((params) => {
        params.set('tab', value);
        if (value !== 'documents') {
          params.delete('document');
          params.delete('run');
        }
        if (value !== 'compare') {
          params.delete('compare');
        }
      });
    },
    [replaceParams],
  );

  const openDocument = useCallback(
    (docId: string, activeRunId?: string | null) => {
      replaceParams((params) => {
        params.set('tab', 'documents');
        params.set('document', docId);
        if (activeRunId) params.set('run', activeRunId);
        else params.delete('run');
      });
    },
    [replaceParams],
  );

  const openCompare = useCallback(
    (ids: string[]) => {
      replaceParams((params) => {
        params.set('tab', 'compare');
        params.set('compare', ids.join(','));
      });
    },
    [replaceParams],
  );

  const documentsPanel =
    documentId || runId ? (
      <DocumentDetailView
        documentId={documentId ?? ''}
        runId={runId}
        onBack={() =>
          replaceParams((params) => {
            params.delete('document');
            params.delete('run');
          })
        }
        onCompare={(id) => openCompare([id])}
      />
    ) : (
      <DocumentsPanelClient onOpenDocument={openDocument} onCompare={openCompare} />
    );

  return (
    <div>
      <h1 className="dar-page-title">Анализатор</h1>
      <p className="dar-page-lead">
        Загрузите документ — получите разбор с фактами, рисками и ссылками на фрагменты текста.
      </p>
      <OnboardingPanel variant="analyzer" />
      <UrlSectionTabs
        ariaLabel="Разделы анализатора"
        value={tab}
        onChange={setTab}
        items={[
          {
            value: 'new',
            label: 'Новый анализ',
            panel: (
              <Suspense fallback={<Skeleton height={240} />}>
                <UploadClient embedded onOpenDocument={openDocument} initialRunId={searchParams.get('run')} />
              </Suspense>
            ),
          },
          {
            value: 'documents',
            label: 'Мои документы',
            panel: documentsPanel,
          },
          {
            value: 'compare',
            label: 'Сравнение',
            panel: <ComparePanelClient presetIds={compareIds} onOpenDocument={openDocument} />,
          },
        ]}
      />
    </div>
  );
}

export default function AnalyzerHubClient() {
  return (
    <Suspense fallback={<Skeleton height={320} />}>
      <AnalyzerHubInner />
    </Suspense>
  );
}

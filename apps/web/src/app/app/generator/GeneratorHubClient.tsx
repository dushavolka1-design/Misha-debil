'use client';

import { Suspense, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { Skeleton } from '@dar/ui';

import { UrlSectionTabs } from '../../../components/UrlSectionTabs';
import { OnboardingPanel } from '../../../components/OnboardingPanel';
import EntryWizardClient from '../entry-wizard/EntryWizardClient';
import FormsCatalogClient from '../forms/FormsCatalogClient';
import CreatedDocumentsPanel from './CreatedDocumentsPanel';

const TAB_VALUES = ['templates', 'wizard', 'created'] as const;
type TabValue = (typeof TAB_VALUES)[number];

function isTabValue(value: string | null): value is TabValue {
  return TAB_VALUES.includes(value as TabValue);
}

function GeneratorHubInner() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const rawTab = searchParams.get('tab');
  const tab: TabValue = isTabValue(rawTab) ? rawTab : 'templates';

  const setTab = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('tab', value);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return (
    <div>
      <h1 className="dar-page-title">Генерация</h1>
      <p className="dar-page-lead">
        Выберите шаблон, пройдите мастер или продолжите черновик — готовые файлы сохраняются в истории.
      </p>
      <OnboardingPanel variant="generator" />
      <UrlSectionTabs
        ariaLabel="Разделы генерации"
        value={tab}
        onChange={setTab}
        items={[
          {
            value: 'templates',
            label: 'Шаблоны',
            panel: (
              <Suspense fallback={<Skeleton height={240} />}>
                <FormsCatalogClient embedded />
              </Suspense>
            ),
          },
          {
            value: 'wizard',
            label: 'Мастер документов',
            panel: (
              <Suspense fallback={<Skeleton height={320} />}>
                <EntryWizardClient embedded />
              </Suspense>
            ),
          },
          {
            value: 'created',
            label: 'Созданные документы',
            panel: <CreatedDocumentsPanel />,
          },
        ]}
      />
    </div>
  );
}

export default function GeneratorHubClient() {
  return (
    <Suspense fallback={<Skeleton height={320} />}>
      <GeneratorHubInner />
    </Suspense>
  );
}

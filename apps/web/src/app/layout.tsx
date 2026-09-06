import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import '@dar/ui/styles.css';
import '../styles/app.css';

export const metadata: Metadata = {
  title: {
    default: 'Docly',
    template: '%s · Docly',
  },
  description:
    'Docly — анализ документов и генерация шаблонов для РФ. Информационный помощник, не замена специалиста.',
  icons: {
    icon: '/docly-logo.png',
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <head>
        {/* Load the local API address before client modules initialize. */}
        <script src="/docly-runtime.js" />
      </head>
      <body>{children}</body>
    </html>
  );
}

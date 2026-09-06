import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@dar/ui', '@dar/contracts', 'lucide-react'],
  eslint: {
    // Typecheck runs via `pnpm typecheck`; ESLint flat config is TS-aware in CI separately.
    ignoreDuringBuilds: true,
  },
  async redirects() {
    return [
      { source: '/app', destination: '/app/analyzer', permanent: false },
      { source: '/app/upload', destination: '/app/analyzer?tab=new', permanent: false },
      { source: '/app/compare', destination: '/app/analyzer?tab=compare', permanent: false },
      { source: '/app/forms', destination: '/app/generator?tab=templates', permanent: false },
      { source: '/app/entry-wizard', destination: '/app/generator?tab=wizard', permanent: false },
      {
        source: '/app/jobs/:id',
        destination: '/app/analyzer?tab=documents&run=:id',
        permanent: false,
      },
      {
        source: '/app/reports/:id',
        destination: '/app/analyzer?tab=documents&run=:id',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;

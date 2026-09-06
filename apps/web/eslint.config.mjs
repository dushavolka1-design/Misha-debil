import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: ['.next/**', 'node_modules/**', 'e2e/**', 'playwright-report/**'],
  },
  {
    // Next.js regenerates this declaration file during next build.
    // Keep lint enabled; permit its generated path reference only here.
    files: ['next-env.d.ts'],
    rules: {
      '@typescript-eslint/triple-slash-reference': [
        'error',
        { path: 'always', types: 'prefer-import', lib: 'always' },
      ],
    },
  },
  {
    // This script executes in the browser, not in Node.js.
    files: ['public/docly-runtime.js'],
    languageOptions: { globals: { window: 'readonly' } },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-unused-vars': 'off',
    },
  },
);

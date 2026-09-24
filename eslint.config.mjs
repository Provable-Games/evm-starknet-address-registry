import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default [
  { files: ['**/*.mjs'], ...js.configs.recommended },
  ...tseslint.configs.strictTypeChecked.map((config) => ({
    ...config,
    files: ['**/*.ts'],
  })),
  {
    files: ['**/*.ts'],
    languageOptions: {
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      'no-warning-comments': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
    },
  },
  {
    files: ['packages/sdk/src/**/*.ts'],
    rules: {
      'no-restricted-globals': [
        'error',
        {
          globals: [
            'window',
            'document',
            'navigator',
            'localStorage',
            'sessionStorage',
            'location',
            'history',
            'fetch',
            'WebSocket',
            'XMLHttpRequest',
            'EventSource',
            'indexedDB',
            'caches',
          ],
          checkGlobalObject: true,
        },
      ],
    },
    languageOptions: {
      parserOptions: {
        project: './packages/sdk/tsconfig.build.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
];

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['packages/sdk/tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['packages/sdk/src/**/*.ts'],
      reporter: ['text', 'json-summary', 'json', 'lcov'],
      thresholds: {
        perFile: true,
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100,
      },
    },
  },
});

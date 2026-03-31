import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/__tests__/**/*.spec.ts', 'src/**/__tests__/**/*.spec.js'],
    testTimeout: 5000,
  },
});

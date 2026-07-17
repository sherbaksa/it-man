/** Author: Dev2 | Date: 2026-07-16 | Purpose: Browser-like smoke-test environment for critical React pages. */
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    restoreMocks: true,
  },
})

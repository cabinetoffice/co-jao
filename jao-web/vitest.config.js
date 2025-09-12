// jao-web/vitest.config.js
import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  root: '.',
  test: {
    environment: 'jsdom',
    globals: true
  },
  resolve: {
    alias: {
      // Match your webpack aliases
      '@': path.resolve(__dirname, './src')
    }
  }
})

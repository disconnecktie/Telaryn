// Configure Telaryn's React build and browser-oriented Vitest environment.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { env } from 'node:process'
import packageMetadata from './package.json' with { type: 'json' }

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_TELARYN_VERSION': JSON.stringify(packageMetadata.version),
    'import.meta.env.VITE_TELARYN_BUILD': JSON.stringify(env.TELARYN_BUILD || 'development'),
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
})

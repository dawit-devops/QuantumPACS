/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      events: 'events',
    },
  },
  optimizeDeps: {
    include: ['events'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router-dom')) return 'vendor-react';
          if (id.includes('node_modules/antd') || id.includes('node_modules/@ant-design')) return 'vendor-antd';
          if (id.includes('node_modules/cornerstone') || id.includes('node_modules/@cornerstonejs') || id.includes('node_modules/dicom-parser') || id.includes('node_modules/hammerjs')) return 'vendor-cornerstone';
        },
      },
    },
    chunkSizeWarningLimit: 4000,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    testTimeout: 60000,
    exclude: ['node_modules/**', 'e2e/**', 'dist/**'],
  },
  define: {
    'process.env': {},
  },
})

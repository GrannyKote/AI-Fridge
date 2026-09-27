import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const apiProxy = {
  '/api': {
    target: process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/ml': {
    target: process.env.VITE_ML_PROXY ?? 'http://127.0.0.1:8001',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/ml/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  server: { host: true, proxy: apiProxy },
  preview: { host: true, proxy: apiProxy },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'favicon.svg', 'apple-touch-icon-180x180.png'],
      manifest: {
        id: '/',
        name: 'AI-Fridge — умный холодильник',
        short_name: 'AI-Fridge',
        description: 'Учёт продуктов, сроков годности и списков покупок',
        lang: 'ru',
        dir: 'ltr',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#0b0c0b',
        theme_color: '#0b0c0b',
        categories: ['food', 'lifestyle', 'productivity'],
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
      devOptions: { enabled: true, type: 'module' },
    }),
  ],
})

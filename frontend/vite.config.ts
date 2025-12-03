import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  // バックエンド切り替え: VITE_BACKEND=python (default) or VITE_BACKEND=typescript
  const backendType = env.VITE_BACKEND || 'python'
  const backendPort = backendType === 'typescript' ? 3000 : 8000
  const backendUrl = env.VITE_BACKEND_URL || `http://localhost:${backendPort}`
  
  console.log(`🔗 Backend: ${backendType} (${backendUrl})`)
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  }
})


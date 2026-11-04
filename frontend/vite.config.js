import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // /api 로 시작하는 요청은 백엔드(uvicorn, 8000)로 넘긴다.
    // 배포에서는 Nginx 가 같은 역할을 해서 프론트와 API 가 한 도메인이 된다 (레퍼런스 14장).
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})

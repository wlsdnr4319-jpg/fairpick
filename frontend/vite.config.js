import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// API 서버 주소. E2E 는 별도 서버(8001, E2E 전용 DB)를 쓰므로 바꿀 수 있게 한다
const API_TARGET = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // /api 로 시작하는 요청은 백엔드(uvicorn, 8000)로 넘긴다.
    // 배포에서는 Nginx 가 같은 역할을 해서 프론트와 API 가 한 도메인이 된다 (레퍼런스 14장).
    proxy: {
      '/api': API_TARGET,
    },
  },
  // vite preview(빌드 결과 확인)도 같은 프록시를 쓴다. E2E 는 이걸로 띄운다
  preview: {
    proxy: {
      '/api': API_TARGET,
    },
  },
  // 단위·컴포넌트 테스트 (Vitest). 브라우저 대신 jsdom, API 는 MSW 로 가짜 응답을 준다.
  // E2E(Playwright)는 e2e/ 에 따로 있다
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
    restoreMocks: true,
    // 여러 파일을 동시에 돌리면 입력 흉내(userEvent.type)가 느려져 기본 5초를 넘기기도 한다
    testTimeout: 15_000,
  },
})

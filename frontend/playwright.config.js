import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

// E2E: 실제 백엔드(E2E 전용 DB, 매번 시드부터 다시)와 빌드한 프론트를 띄워 브라우저로 사용자 흐름을 확인한다.
// 실행: npm run e2e  (Docker MySQL 이 켜져 있어야 한다. docs/testing.md)
const API_PORT = 8001
const WEB_PORT = 4173

const backendDir = fileURLToPath(new URL('../backend', import.meta.url))
// 로컬은 backend 가상환경의 파이썬, CI 는 setup-python 의 python
const venvPython = ['.venv/Scripts/python.exe', '.venv/bin/python']
  .map((p) => `${backendDir}/${p}`)
  .find((p) => existsSync(p))
const python = process.env.E2E_PYTHON ?? venvPython ?? 'python'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // 같은 DB 를 쓰므로 순서대로
  workers: 1,
  forbidOnly: !!process.env.CI,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    // 모바일 화면(375px)에서도 핵심 흐름이 되는지
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command: `"${python}" -m app.scripts.e2e_server --port ${API_PORT}`,
      cwd: backendDir,
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      timeout: 120_000,
      reuseExistingServer: false, // 항상 DB 를 비우고 시드부터 시작
      stdout: 'pipe',
      // E2E 에서 올린 표지 이미지는 개발용 backend/uploads 와 섞이지 않게 따로 둔다 (git 무시)
      env: { UPLOAD_DIR: 'uploads-e2e' },
    },
    {
      command: `npm run build && npx vite preview --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: { API_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
    },
  ],
})

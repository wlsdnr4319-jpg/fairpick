import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { setAccessToken } from '../store/auth'
import { server } from './server'

// findBy·waitFor 기본 대기(1초)는 CI·첫 실행처럼 느린 환경에서 부족해 늘린다
configure({ asyncUtilTimeout: 5000 })

// 처리하지 않은 요청이 있으면 테스트를 실패시킨다 (빠진 가짜 응답을 바로 알 수 있다)
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  setAccessToken(null)
  sessionStorage.clear()
})
afterAll(() => server.close())

import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

// 테스트용 가짜 API. 기본은 '로그인 안 한 상태'이고, 테스트마다 server.use(...) 로 덮어쓴다
export const API = '*/api/v1'

export const json = (body, status = 200) => HttpResponse.json(body, { status })
export const apiError = (status, code, message = '오류') => json({ error: { code, message } }, status)

export const defaultHandlers = [
  http.post(`${API}/auth/refresh`, () => apiError(401, 'NOT_AUTHENTICATED', '로그인이 필요해요')),
  http.get(`${API}/auth/oauth/providers`, () => json({ providers: [] })),
  http.get(`${API}/categories`, () => json([])),
  http.get(`${API}/tags`, () => json([])),
  http.get(`${API}/venues`, () => json([])),
]

export const server = setupServer(...defaultHandlers)

// 앱 시작 때 /auth/refresh 로 로그인이 복구되는 사용자
export function loggedInAs(user = USER) {
  server.use(http.post(`${API}/auth/refresh`, () => json({ access_token: 'access-1', user })))
  return user
}

export const USER = { id: 1, email: 'me@example.com', nickname: '지누', role: 'user' }

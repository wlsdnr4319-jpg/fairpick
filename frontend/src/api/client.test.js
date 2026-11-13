import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { getAccessToken, setAccessToken } from '../store/auth'
import { API, apiError, json, server } from '../test/server'
import { api, errorCode, errorMessage } from './client'

// 액세스 토큰이 'new' 면 성공, 아니면 만료 응답을 주는 보호된 API
function protectedEndpoint(path = '/me') {
  const seen = []
  server.use(
    http.get(`${API}${path}`, ({ request }) => {
      const auth = request.headers.get('Authorization')
      seen.push(auth)
      return auth === 'Bearer new' ? json({ ok: true }) : apiError(401, 'TOKEN_EXPIRED', '만료')
    }),
  )
  return seen
}

describe('api 클라이언트 토큰 처리', () => {
  it('메모리의 액세스 토큰을 Authorization 헤더로 보낸다', async () => {
    const seen = protectedEndpoint()
    setAccessToken('new')
    await api.get('/me')
    expect(seen).toEqual(['Bearer new'])
  })

  it('토큰이 만료되면 재발급받고 원래 요청을 다시 보낸다', async () => {
    const seen = protectedEndpoint()
    server.use(http.post(`${API}/auth/refresh`, () => json({ access_token: 'new', user: {} })))
    setAccessToken('old')

    const res = await api.get('/me')

    expect(res.data).toEqual({ ok: true })
    expect(seen).toEqual(['Bearer old', 'Bearer new'])
    expect(getAccessToken()).toBe('new')
  })

  it('동시에 여러 요청이 만료돼도 재발급은 한 번만 보낸다 (리프레시 토큰 재사용 탐지 방지)', async () => {
    protectedEndpoint('/a')
    protectedEndpoint('/b')
    protectedEndpoint('/c')
    let refreshCalls = 0
    server.use(
      http.post(`${API}/auth/refresh`, async () => {
        refreshCalls += 1
        await new Promise((r) => setTimeout(r, 20))
        return json({ access_token: 'new', user: {} })
      }),
    )
    setAccessToken('old')

    const results = await Promise.all([api.get('/a'), api.get('/b'), api.get('/c')])

    expect(results.map((r) => r.status)).toEqual([200, 200, 200])
    expect(refreshCalls).toBe(1)
  })

  it('재발급도 실패하면 토큰을 지우고 원래 에러를 돌려준다', async () => {
    protectedEndpoint()
    server.use(http.post(`${API}/auth/refresh`, () => apiError(401, 'REFRESH_INVALID')))
    setAccessToken('old')

    const error = await api.get('/me').catch((e) => e)

    expect(errorCode(error)).toBe('TOKEN_EXPIRED')
    expect(getAccessToken()).toBeNull()
  })

  it('만료가 아닌 401 은 재발급하지 않는다', async () => {
    let refreshCalls = 0
    server.use(
      http.get(`${API}/me`, () => apiError(401, 'NOT_AUTHENTICATED')),
      http.post(`${API}/auth/refresh`, () => {
        refreshCalls += 1
        return json({ access_token: 'new', user: {} })
      }),
    )
    await expect(api.get('/me')).rejects.toBeTruthy()
    expect(refreshCalls).toBe(0)
  })
})

describe('errorMessage', () => {
  it('서버의 { error: { message } } 를 그대로 쓴다', async () => {
    server.use(http.get(`${API}/x`, () => apiError(409, 'EMAIL_TAKEN', '이미 가입된 이메일이에요')))
    const error = await api.get('/x').catch((e) => e)
    expect(errorMessage(error)).toBe('이미 가입된 이메일이에요')
  })

  it('네트워크 오류처럼 응답 본문이 없으면 기본 문구', () => {
    expect(errorMessage(new Error('Network Error'))).toBe('잠시 후 다시 시도해 주세요')
  })
})

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { Route } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { GuestOnlyRoute } from '../routes/Guards'
import { getAccessToken } from '../store/auth'
import { currentLocation, renderApp } from '../test/render'
import { API, apiError, json, server, USER } from '../test/server'
import Login from './Login'
import Signup from './Signup'

// 앱(App.jsx)과 같이 로그인·가입 화면을 GuestOnlyRoute 안에 둔다. 로그인 직후 가드가 다시 그려지는 것까지 확인한다
const routes = (
  <>
    <Route element={<GuestOnlyRoute />}>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
    </Route>
    <Route path="*" element={<p>다른 화면</p>} />
  </>
)

function loginEndpoint() {
  const bodies = []
  server.use(
    http.post(`${API}/auth/login`, async ({ request }) => {
      const body = await request.json()
      bodies.push(body)
      return body.password === 'correct-pw'
        ? json({ access_token: 'access-1', token_type: 'bearer', expires_in: 1800, user: USER })
        : apiError(401, 'INVALID_CREDENTIALS', '이메일 또는 비밀번호가 맞지 않아요')
    }),
  )
  return bodies
}

async function fillLogin(password) {
  await userEvent.type(await screen.findByLabelText('이메일'), 'me@example.com')
  await userEvent.type(screen.getByLabelText('비밀번호'), password)
  await userEvent.click(screen.getByRole('button', { name: '로그인' }))
}

describe('로그인', () => {
  it('성공하면 토큰을 메모리에 두고 원래 페이지로 돌아간다', async () => {
    loginEndpoint()
    renderApp(routes, { route: '/login?next=%2Ffairs%2F3' })
    await fillLogin('correct-pw')

    expect(await screen.findByText('다른 화면')).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/fairs/3')
    expect(getAccessToken()).toBe('access-1')
  })

  it('외부 주소로는 돌아가지 않는다 (오픈 리다이렉트 방지)', async () => {
    loginEndpoint()
    renderApp(routes, { route: '/login?next=%2F%2Fevil.example' })
    await fillLogin('correct-pw')

    await screen.findByText('다른 화면')
    expect(currentLocation(screen)).toBe('/')
  })

  it('실패하면 서버 문구를 보여 주고 머문다', async () => {
    loginEndpoint()
    renderApp(routes, { route: '/login' })
    await fillLogin('wrong-pw')

    expect(await screen.findByRole('alert')).toHaveTextContent('이메일 또는 비밀번호가 맞지 않아요')
    expect(currentLocation(screen)).toBe('/login')
    expect(getAccessToken()).toBeNull()
  })

  it('소셜 로그인 키가 없으면 소셜 버튼을 숨긴다', async () => {
    renderApp(routes, { route: '/login' })
    await screen.findByLabelText('이메일')
    expect(screen.queryByRole('button', { name: /계속하기/ })).not.toBeInTheDocument()
  })

  it('키가 있는 제공자만 버튼을 보여 준다', async () => {
    server.use(http.get(`${API}/auth/oauth/providers`, () => json({ providers: ['kakao', 'unknown'] })))
    renderApp(routes, { route: '/login' })
    expect(await screen.findByRole('button', { name: '카카오로 계속하기' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Google로 계속하기' })).not.toBeInTheDocument()
  })
})

describe('회원가입', () => {
  async function fillSignup({ password = 'password-1', over14 = true } = {}) {
    await userEvent.type(await screen.findByLabelText('이메일'), 'new@example.com')
    await userEvent.type(screen.getByLabelText('비밀번호 (8자 이상)'), password)
    await userEvent.type(screen.getByLabelText('닉네임'), '새 회원')
    if (over14) await userEvent.click(screen.getByLabelText('만 14세 이상입니다'))
  }

  it('만 14세 확인 없이는 요청을 보내지 않는다', async () => {
    let called = false
    server.use(http.post(`${API}/auth/signup`, () => ((called = true), json({}, 201))))
    renderApp(routes, { route: '/signup' })
    await fillSignup({ over14: false })
    await userEvent.click(screen.getByRole('button', { name: '가입하기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('만 14세 이상만 가입할 수 있어요')
    expect(called).toBe(false)
  })

  it('가입하면 바로 로그인해서 홈으로 간다', async () => {
    const signups = []
    server.use(
      http.post(`${API}/auth/signup`, async ({ request }) => {
        signups.push(await request.json())
        return json(USER, 201)
      }),
    )
    const logins = loginEndpoint()
    renderApp(routes, { route: '/signup' })
    await fillSignup({ password: 'correct-pw' })
    await userEvent.click(screen.getByRole('button', { name: '가입하기' }))

    await screen.findByText('다른 화면')
    expect(currentLocation(screen)).toBe('/')
    expect(signups[0]).toEqual({ email: 'new@example.com', password: 'correct-pw', nickname: '새 회원', is_over_14: true })
    expect(logins[0]).toEqual({ email: 'new@example.com', password: 'correct-pw' })
  })

  it('이미 가입된 이메일이면 서버 문구', async () => {
    server.use(http.post(`${API}/auth/signup`, () => apiError(409, 'EMAIL_TAKEN', '이미 가입된 이메일이에요')))
    renderApp(routes, { route: '/signup' })
    await fillSignup()
    await userEvent.click(screen.getByRole('button', { name: '가입하기' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('이미 가입된 이메일이에요')
  })
})

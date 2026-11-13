import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { Route } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from '../routes/Guards'
import { getAccessToken } from '../store/auth'
import { currentLocation, renderApp, renderPage } from '../test/render'
import { API, apiError, json, loggedInAs, server, USER } from '../test/server'
import { MyVisits, NotificationSettings, ResetPassword, Unsubscribe } from './Account'
import { Settings } from './MyPage'

const SETTINGS = { email_enabled: true, prereg_deadline: true, opening_soon: true, fair_updated: false }

function settingsEndpoints() {
  const saved = []
  server.use(
    http.get(`${API}/me/notification-settings`, () => json(SETTINGS)),
    http.put(`${API}/me/notification-settings`, async ({ request }) => {
      const body = await request.json()
      saved.push(body)
      return json(body)
    }),
    http.get(`${API}/push/config`, () => json({ enabled: false, public_key: null })),
  )
  return saved
}

describe('비밀번호 재설정', () => {
  it('메일 요청: 가입 여부와 상관없이 서버가 준 같은 문구를 보여 준다', async () => {
    let sent
    server.use(
      http.post(`${API}/auth/password-reset/request`, async ({ request }) => {
        sent = await request.json()
        return json({ message: '가입된 이메일이면 재설정 링크를 보냈어요' })
      }),
    )
    renderPage(<ResetPassword />, { path: '/reset-password' })
    await userEvent.type(screen.getByLabelText('가입한 이메일'), 'me@example.com')
    await userEvent.click(screen.getByRole('button', { name: '재설정 링크 받기' }))

    expect(await screen.findByRole('status')).toHaveTextContent('가입된 이메일이면 재설정 링크를 보냈어요')
    expect(sent).toEqual({ email: 'me@example.com' })
  })

  it('메일 링크(?token=)로 오면 새 비밀번호를 받고, 바꾸면 로그인 화면으로', async () => {
    let sent
    server.use(
      http.post(`${API}/auth/password-reset/confirm`, async ({ request }) => {
        sent = await request.json()
        return json({ message: 'ok' })
      }),
    )
    renderPage(<ResetPassword />, { path: '/reset-password', route: '/reset-password?token=abcdefghij12' })
    await userEvent.type(screen.getByLabelText('새 비밀번호 (8자 이상)'), 'new-password-1')
    await userEvent.click(screen.getByRole('button', { name: '비밀번호 바꾸기' }))

    await waitFor(() => expect(currentLocation(screen)).toBe('/login'))
    expect(sent).toEqual({ token: 'abcdefghij12', new_password: 'new-password-1' })
  })

  it('8자 미만이면 보내지 않는다', async () => {
    let called = false
    server.use(http.post(`${API}/auth/password-reset/confirm`, () => ((called = true), json({}))))
    renderPage(<ResetPassword />, { path: '/reset-password', route: '/reset-password?token=abcdefghij12' })
    // minLength 검사는 브라우저가 하므로, 앱 자체 검사를 보려고 required 를 피한 짧은 값으로 제출
    const input = screen.getByLabelText('새 비밀번호 (8자 이상)')
    input.removeAttribute('minLength')
    await userEvent.type(input, 'short')
    await userEvent.click(screen.getByRole('button', { name: '비밀번호 바꾸기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('8자 이상')
    expect(called).toBe(false)
  })

  it('만료된 링크면 서버 문구', async () => {
    server.use(http.post(`${API}/auth/password-reset/confirm`, () => apiError(400, 'RESET_TOKEN_INVALID', '링크가 만료됐어요')))
    renderPage(<ResetPassword />, { path: '/reset-password', route: '/reset-password?token=abcdefghij12' })
    await userEvent.type(screen.getByLabelText('새 비밀번호 (8자 이상)'), 'new-password-1')
    await userEvent.click(screen.getByRole('button', { name: '비밀번호 바꾸기' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('링크가 만료됐어요')
  })
})

describe('수신 거부', () => {
  it('링크를 열기만 해서는 처리하지 않고(메일 미리보기 방지), 버튼을 눌러야 보낸다', async () => {
    const tokens = []
    server.use(
      http.post(`${API}/notifications/unsubscribe`, async ({ request }) => {
        tokens.push((await request.json()).token)
        return json({ message: '알림 메일을 더 보내지 않을게요' })
      }),
    )
    renderPage(<Unsubscribe />, { path: '/unsubscribe', route: '/unsubscribe?token=tok-1' })
    await screen.findByRole('button', { name: '알림 메일 그만 받기' })
    expect(tokens).toEqual([])

    await userEvent.click(screen.getByRole('button', { name: '알림 메일 그만 받기' }))
    expect(await screen.findByRole('status')).toHaveTextContent('알림 메일을 더 보내지 않을게요')
    expect(tokens).toEqual(['tok-1'])
  })
})

describe('알림 설정', () => {
  it('하나를 바꾸면 나머지 값과 함께 전체를 저장한다', async () => {
    loggedInAs()
    const saved = settingsEndpoints()
    renderPage(<NotificationSettings />)
    await userEvent.click(await screen.findByLabelText('개막 3일 전'))
    await waitFor(() => expect(saved).toEqual([{ ...SETTINGS, opening_soon: false }]))
    expect(screen.getByLabelText('개막 3일 전')).not.toBeChecked()
  })

  it('이메일 없이 소셜로 가입한 회원에게는 메일 설정 대신 안내', async () => {
    loggedInAs({ ...USER, email: null })
    settingsEndpoints()
    renderPage(<NotificationSettings />)
    expect(await screen.findByText(/알림 메일은 받을 수 없어요/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/로 알림 메일 받기/)).not.toBeInTheDocument()
  })

  it('서버에 푸시 키가 없으면 브라우저 알림 항목을 숨긴다', async () => {
    loggedInAs()
    settingsEndpoints()
    renderPage(<NotificationSettings />)
    await screen.findByText('받을 소식')
    expect(screen.queryByText('브라우저 알림')).not.toBeInTheDocument()
  })
})

describe('관람 노트 모아보기', () => {
  it('없으면 남기는 방법을 알려 준다', async () => {
    server.use(http.get(`${API}/me/visits`, () => json([])))
    renderPage(<MyVisits />)
    expect(await screen.findByText(/'다녀왔어요'를 눌러 기록해 보세요/)).toBeInTheDocument()
  })

  it('박람회 링크, 공개 여부, 좋아요 수', async () => {
    server.use(
      http.get(`${API}/me/visits`, () =>
        json([
          { id: 1, fair_id: 7, fair_title: '서울카페쇼', visited_on: '2026-11-12', rating: 5, memo: '라테', is_public: true, like_count: 3 },
          { id: 2, fair_id: 8, fair_title: '펫쇼', visited_on: null, rating: null, memo: null, is_public: false, like_count: 0 },
        ]),
      ),
    )
    renderPage(<MyVisits />)
    expect(await screen.findByRole('link', { name: '서울카페쇼' })).toHaveAttribute('href', '/fairs/7')
    expect(screen.getByText('2026-11-12 · ★★★★★ · 공개 · ♥ 3')).toBeInTheDocument()
    expect(screen.getByText('날짜 미입력 · 별점 없음 · 나만 보기')).toBeInTheDocument()
  })
})

describe('회원 탈퇴', () => {
  const routes = (
    <>
      <Route path="/" element={<p>홈</p>} />
      <Route element={<ProtectedRoute />}>
        <Route path="/mypage/settings" element={<Settings />} />
      </Route>
    </>
  )

  it('확인하면 탈퇴하고, 메모리의 토큰까지 지운 뒤 홈으로', async () => {
    // 토큰이 남아 있으면 이후 모든 요청이 '없는 사용자' 토큰이라 401 로 실패한다
    loggedInAs()
    settingsEndpoints()
    let deleted = false
    server.use(
      http.delete(`${API}/me`, () => {
        deleted = true
        return new Response(null, { status: 204 })
      }),
    )
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderApp(routes, { route: '/mypage/settings' })
    await userEvent.click(await screen.findByRole('button', { name: '탈퇴하기' }))

    expect(await screen.findByText('홈')).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/') // 로그인 화면(?next=/mypage/settings)으로 새지 않는다
    expect(deleted).toBe(true)
    expect(getAccessToken()).toBeNull()
  })

  it('확인 창에서 취소하면 아무것도 하지 않는다', async () => {
    loggedInAs()
    settingsEndpoints()
    let deleted = false
    server.use(http.delete(`${API}/me`, () => ((deleted = true), new Response(null, { status: 204 }))))
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderApp(routes, { route: '/mypage/settings' })
    await userEvent.click(await screen.findByRole('button', { name: '탈퇴하기' }))
    expect(deleted).toBe(false)
    expect(screen.getByRole('heading', { name: '계정 설정' })).toBeInTheDocument()
  })
})

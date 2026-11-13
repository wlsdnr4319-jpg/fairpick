import { screen } from '@testing-library/react'
import { Route } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { loggedInAs, USER } from '../test/server'
import { currentLocation, renderApp } from '../test/render'
import { AdminRoute, GuestOnlyRoute, ProtectedRoute } from './Guards'

const routes = (
  <>
    <Route path="/" element={<p>홈</p>} />
    <Route path="/login" element={<p>로그인 화면</p>} />
    <Route element={<GuestOnlyRoute />}>
      <Route path="/signup" element={<p>가입 화면</p>} />
    </Route>
    <Route element={<ProtectedRoute />}>
      <Route path="/mypage" element={<p>마이페이지</p>} />
    </Route>
    <Route element={<AdminRoute />}>
      <Route path="/admin" element={<p>관리자 화면</p>} />
    </Route>
  </>
)

describe('ProtectedRoute', () => {
  it('로그인 복구를 기다리는 동안 내용을 보여 주지 않는다', () => {
    loggedInAs()
    renderApp(routes, { route: '/mypage' })
    expect(screen.getByText('확인 중…')).toBeInTheDocument()
    expect(screen.queryByText('마이페이지')).not.toBeInTheDocument()
  })

  it('로그인했으면 보여 준다', async () => {
    loggedInAs()
    renderApp(routes, { route: '/mypage' })
    expect(await screen.findByText('마이페이지')).toBeInTheDocument()
  })

  it('비로그인이면 돌아올 주소를 붙여 로그인 화면으로 보낸다', async () => {
    renderApp(routes, { route: '/mypage?tab=2' })
    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/login?next=%2Fmypage%3Ftab%3D2')
  })
})

describe('AdminRoute', () => {
  it('일반 회원에게는 안내만 보여 준다', async () => {
    loggedInAs({ ...USER, role: 'user' })
    renderApp(routes, { route: '/admin' })
    expect(await screen.findByText('관리자만 이용할 수 있어요')).toBeInTheDocument()
    expect(screen.queryByText('관리자 화면')).not.toBeInTheDocument()
  })

  it('관리자면 보여 준다', async () => {
    loggedInAs({ ...USER, role: 'admin' })
    renderApp(routes, { route: '/admin' })
    expect(await screen.findByText('관리자 화면')).toBeInTheDocument()
  })

  it('비로그인이면 로그인 화면으로', async () => {
    renderApp(routes, { route: '/admin' })
    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
  })
})

describe('GuestOnlyRoute', () => {
  it('이미 로그인했으면 가입 화면 대신 홈으로', async () => {
    loggedInAs()
    renderApp(routes, { route: '/signup' })
    expect(await screen.findByText('홈')).toBeInTheDocument()
  })

  it('next 가 있으면 홈 대신 그 주소로 (로그인 성공 직후 경쟁 방지)', async () => {
    loggedInAs()
    renderApp(routes, { route: '/signup?next=%2Fmypage' })
    expect(await screen.findByText('마이페이지')).toBeInTheDocument()
  })

  it('next 가 외부 주소면 홈으로', async () => {
    loggedInAs()
    renderApp(routes, { route: '/signup?next=%2F%2Fevil.example' })
    expect(await screen.findByText('홈')).toBeInTheDocument()
  })

  it('비로그인이면 가입 화면', async () => {
    renderApp(routes, { route: '/signup' })
    expect(await screen.findByText('가입 화면')).toBeInTheDocument()
  })
})

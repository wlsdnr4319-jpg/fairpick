import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { Route } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { currentLocation, renderApp } from '../test/render'
import { API, json, loggedInAs, server } from '../test/server'
import Layout from './Layout'

const renderLayout = (route = '/') =>
  renderApp(
    <Route element={<Layout />}>
      <Route path="*" element={<p>본문</p>} />
    </Route>,
    { route },
  )

// 데스크톱 사이드바 (jsdom 은 CSS 를 적용하지 않아 휴대폰용 위쪽 바도 함께 그려진다)
const desktop = () => screen.getByRole('complementary')

describe('공통 레이아웃', () => {
  it('첫 Tab 에 본문으로 건너뛰는 링크가 있다', async () => {
    renderLayout()
    await userEvent.tab()
    const skip = screen.getByRole('link', { name: '본문으로 건너뛰기' })
    expect(skip).toHaveFocus()
    expect(skip).toHaveAttribute('href', '#main')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main')
  })

  it('사이드바에 자주 쓰는 목록 바로가기와 카테고리가 있고, 지금 메뉴를 표시한다', async () => {
    server.use(http.get(`${API}/categories`, () => json([{ code: 'food', name: '식음료' }])))
    renderLayout('/fairs?period=this_weekend&free=true')
    const side = desktop()
    expect(within(side).getByRole('link', { name: '이번 주말' })).toHaveAttribute('aria-current', 'page')
    expect(within(side).getByRole('link', { name: '박람회 찾기' })).not.toHaveAttribute('aria-current')
    expect(within(side).getByRole('link', { name: '사전등록 마감 임박' })).toHaveAttribute('href', '/fairs?sort=prereg_deadline')
    expect(await within(side).findByRole('link', { name: '식음료' })).toHaveAttribute('href', '/fairs?category=food')
    // 로그인 전에는 내 메뉴·관리 메뉴가 없다
    expect(within(side).queryByRole('link', { name: '북마크' })).not.toBeInTheDocument()
    expect(within(side).getByRole('link', { name: '회원가입' })).toBeInTheDocument()
  })

  it('로그인하면 내 메뉴와 닉네임·로그아웃, 관리자에게는 관리 메뉴', async () => {
    loggedInAs({ id: 1, email: 'a@example.com', nickname: '관리인', role: 'admin' })
    renderLayout()
    const side = desktop()
    expect(await within(side).findByText('관리인')).toBeInTheDocument()
    expect(within(side).getByRole('link', { name: '관람 노트' })).toHaveAttribute('href', '/mypage/visits')
    expect(within(side).getByRole('link', { name: '수집 검수' })).toHaveAttribute('href', '/admin/review')
    expect(within(side).getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
  })

  it('휴대폰 메뉴: ☰ 로 열고, 메뉴를 누르면 이동하며 닫힌다', async () => {
    const user = userEvent.setup()
    renderLayout()
    const open = screen.getByRole('button', { name: '메뉴 열기' })
    expect(open).toHaveAttribute('aria-expanded', 'false')
    await user.click(open)

    const drawer = screen.getByRole('dialog', { name: '메뉴' })
    expect(open).toHaveAttribute('aria-expanded', 'true')
    expect(document.body.style.overflow).toBe('hidden') // 뒤 화면 스크롤 막음
    expect(within(drawer).getByRole('button', { name: '메뉴 닫기' })).toHaveFocus()

    await user.click(within(drawer).getByRole('link', { name: '통계' }))
    expect(currentLocation(screen)).toBe('/report')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(document.body.style.overflow).toBe('')
  })

  it('휴대폰 메뉴: Esc 로 닫으면 ☰ 버튼으로 포커스가 돌아온다', async () => {
    const user = userEvent.setup()
    renderLayout()
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: '메뉴 열기' })).toHaveFocus()
  })
})

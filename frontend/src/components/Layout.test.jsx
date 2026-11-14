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
const top = () => screen.getByRole('banner')

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
    // 로그인·회원가입은 사이드바가 아니라 위쪽 바 오른쪽에
    expect(within(side).queryByRole('link', { name: '회원가입' })).not.toBeInTheDocument()
    expect(await within(top()).findByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/signup')
    expect(within(top()).getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })

  it('위쪽 바: 검색어로 목록을 열고, 이번 주말 박람회 수를 보여 준다', async () => {
    server.use(http.get(`${API}/fairs`, () => json({ items: [], page: 1, size: 1, total: 12 })))
    const user = userEvent.setup()
    renderLayout('/calendar')
    expect(await within(top()).findByRole('link', { name: '이번 주말 박람회 12개' })).toHaveAttribute('href', '/fairs?period=this_weekend')
    await user.type(within(top()).getByRole('searchbox', { name: '박람회 이름·키워드' }), '커피{Enter}')
    expect(currentLocation(screen)).toBe('/fairs?q=%EC%BB%A4%ED%94%BC')
  })

  it('로그인하면 사이드바에 내 메뉴·관리 메뉴, 위쪽 바에 계정 메뉴', async () => {
    loggedInAs({ id: 1, email: 'a@example.com', nickname: '관리인', role: 'admin' })
    const user = userEvent.setup()
    renderLayout()
    const side = desktop()
    expect(await within(side).findByRole('link', { name: '관람 노트' })).toHaveAttribute('href', '/mypage/visits')
    expect(within(side).getByRole('link', { name: '수집 검수' })).toHaveAttribute('href', '/admin/review')
    expect(within(side).queryByRole('button', { name: '로그아웃' })).not.toBeInTheDocument()

    const account = within(top()).getByRole('button', { name: '계정 메뉴 (관리인)' })
    expect(account).toHaveAttribute('aria-expanded', 'false')
    await user.click(account)
    expect(account).toHaveAttribute('aria-expanded', 'true')
    expect(within(top()).getByText('a@example.com')).toBeInTheDocument()
    expect(within(top()).getByRole('link', { name: '관리자 홈' })).toHaveAttribute('href', '/admin')

    // Esc 로 닫으면 버튼으로 포커스가 돌아온다
    await user.keyboard('{Escape}')
    expect(within(top()).queryByRole('link', { name: '관리자 홈' })).not.toBeInTheDocument()
    expect(account).toHaveFocus()

    // 메뉴의 링크로 이동하면 닫힌다
    await user.click(account)
    await user.click(within(top()).getByRole('link', { name: '관람 노트' }))
    expect(currentLocation(screen)).toBe('/mypage/visits')
    expect(account).toHaveAttribute('aria-expanded', 'false')
  })

  it('계정 메뉴에서 로그아웃하면 홈으로 가고 로그인 버튼이 다시 보인다', async () => {
    loggedInAs()
    const user = userEvent.setup()
    renderLayout('/report')
    await user.click(await within(top()).findByRole('button', { name: /^계정 메뉴/ }))
    await user.click(within(top()).getByRole('button', { name: '로그아웃' }))
    expect(await within(top()).findByRole('link', { name: '로그인' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/')
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

import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { currentLocation, renderApp } from '../test/render'
import Layout from './Layout'

const renderLayout = (route = '/') =>
  renderApp(
    <Route element={<Layout />}>
      <Route path="*" element={<p>본문</p>} />
    </Route>,
    { route },
  )

describe('공통 레이아웃', () => {
  it('첫 Tab 에 본문으로 건너뛰는 링크가 있다', async () => {
    renderLayout()
    await userEvent.tab()
    const skip = screen.getByRole('link', { name: '본문으로 건너뛰기' })
    expect(skip).toHaveFocus()
    expect(skip).toHaveAttribute('href', '#main')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main')
  })

  it('휴대폰용 메뉴에도 캘린더·통계가 있다 (전에는 휴대폰에서 숨겨져 갈 방법이 없었다)', async () => {
    renderLayout()
    // 데스크톱용·휴대폰용 둘째 줄 메뉴가 같은 링크를 가진다 (CSS 로 하나만 보인다)
    const menus = screen.getAllByRole('navigation', { name: '둘러보기' })
    expect(menus).toHaveLength(2)
    for (const menu of menus) {
      expect(within(menu).getAllByRole('link').map((a) => a.textContent)).toEqual(['박람회 찾기', '캘린더', '통계'])
    }
    await userEvent.click(within(menus[1]).getByRole('link', { name: '통계' }))
    expect(currentLocation(screen)).toBe('/report')
  })
})

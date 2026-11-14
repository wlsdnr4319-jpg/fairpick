import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { makeFair } from '../test/fixtures'
import { currentLocation, renderPage } from '../test/render'
import FairCard from './FairCard'

describe('박람회 카드', () => {
  it('제목이 상세 링크이고, 북마크 버튼은 링크 안에 들어가지 않는다', async () => {
    const fair = makeFair({ id: 7, title: '커피 엑스포' })
    renderPage(<FairCard fair={fair} />, { path: '/fairs', route: '/fairs' })

    const link = screen.getByRole('link', { name: '커피 엑스포' })
    expect(link).toHaveAttribute('href', '/fairs/7')
    const bookmark = screen.getByRole('button', { name: '북마크' })
    // <a> 안의 <button> 은 HTML 규칙 위반이고 스크린리더가 링크 이름에 버튼까지 섞어 읽는다
    expect(bookmark.closest('a')).toBeNull()

    await userEvent.click(link)
    expect(currentLocation(screen)).toBe('/fairs/7')
  })

  it('끝난 박람회는 표지만 흑백이고 글자는 흐리게 하지 않는다 (대비 유지)', () => {
    renderPage(<FairCard fair={makeFair({ title: '지난 박람회', progress: 'ended', d_day: null })} />)
    const card = screen.getByRole('article')
    expect(card).toHaveAttribute('data-ended', 'true')
    expect(card.className).not.toMatch(/opacity-/)
  })
})

import { describe, expect, it } from 'vitest'
import { activeLink, safeNext } from './nav'

describe('safeNext (로그인 후 돌아갈 주소)', () => {
  it('사이트 안 경로는 그대로', () => {
    expect(safeNext('/fairs?category=food')).toBe('/fairs?category=food')
  })

  it.each([
    ['https://evil.example', '외부 주소'],
    ['//evil.example', '프로토콜 생략 외부 주소'],
    ['javascript:alert(1)', '스크립트'],
    [null, '없음'],
    ['', '빈 값'],
  ])('%s (%s) → 홈', (next) => {
    expect(safeNext(next)).toBe('/')
  })
})

describe('사이드바 현재 메뉴', () => {
  const links = ['/', '/fairs', '/fairs?period=this_weekend', '/fairs?sort=prereg_deadline', '/fairs?category=food', '/mypage', '/mypage/visits']
  const at = (path) => {
    const [pathname, search = ''] = path.split('?')
    return activeLink(links, { pathname, search: search ? `?${search}` : '' })
  }

  it('필터 바로가기가 맞으면 그 메뉴, 아니면 박람회 찾기', () => {
    expect(at('/fairs')).toBe('/fairs')
    expect(at('/fairs?period=this_weekend')).toBe('/fairs?period=this_weekend')
    // 바로가기에서 필터를 더 붙여도 그 메뉴가 켜져 있다
    expect(at('/fairs?period=this_weekend&free=true')).toBe('/fairs?period=this_weekend')
    expect(at('/fairs?category=food&page=2')).toBe('/fairs?category=food')
    expect(at('/fairs?category=art')).toBe('/fairs')
  })

  it('경로가 정확히 같을 때만 켠다 (홈이 모든 페이지에서 켜지지 않게)', () => {
    expect(at('/')).toBe('/')
    expect(at('/mypage/visits')).toBe('/mypage/visits')
    expect(at('/fairs/12')).toBeNull()
  })
})

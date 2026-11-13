import { describe, expect, it } from 'vitest'
import { safeNext } from './nav'

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

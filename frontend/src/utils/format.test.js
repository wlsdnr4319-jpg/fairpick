import { afterEach, describe, expect, it, vi } from 'vitest'
import { deadlineDDay, formatDateTime, formatDistance, formatPeriod, formatPrice, statusLabel } from './format'

describe('formatPeriod', () => {
  it('같은 해면 연도 없이 월.일(요일)', () => {
    expect(formatPeriod('2026-11-19', '2026-11-22')).toBe('11.19(목) ~ 11.22(일)')
  })

  it('하루짜리 행사는 날짜 하나만', () => {
    expect(formatPeriod('2026-11-19', '2026-11-19')).toBe('11.19(목)')
  })

  it('해를 넘기면 연도를 붙인다', () => {
    expect(formatPeriod('2026-12-30', '2027-01-02')).toBe('2026.12.30(수) ~ 2027.1.2(토)')
  })
})

describe('formatDateTime', () => {
  it('서버가 준 +09:00 일시를 시간대 변환 없이 그대로 보여 준다', () => {
    expect(formatDateTime('2026-11-16T23:59:00+09:00')).toBe('11.16(월) 23:59')
  })

  it('값이 없으면 빈 문자열', () => {
    expect(formatDateTime(null)).toBe('')
  })
})

describe('formatPrice', () => {
  it.each([
    [null, '확인 중'],
    [undefined, '확인 중'],
    [0, '무료'],
    [15000, '15,000원'],
  ])('%s → %s', (value, expected) => {
    expect(formatPrice(value)).toBe(expected)
  })
})

describe('statusLabel', () => {
  it.each([
    ['ongoing', 0, '진행 중'],
    ['ended', -3, '종료'],
    ['upcoming', 0, 'D-day'],
    ['upcoming', 6, 'D-6'],
  ])('%s, D%s → %s', (progress, dDay, expected) => {
    expect(statusLabel(progress, dDay)).toBe(expected)
  })
})

describe('deadlineDDay', () => {
  afterEach(() => vi.useRealTimers())

  it('마감까지 남은 날을 내림해서 센다', () => {
    vi.useFakeTimers({ now: new Date('2026-11-13T12:00:00+09:00') })
    expect(deadlineDDay('2026-11-16T23:59:00+09:00')).toBe(3)
    expect(deadlineDDay('2026-11-13T23:59:00+09:00')).toBe(0)
  })

  it('이미 지났거나 값이 없으면 null', () => {
    vi.useFakeTimers({ now: new Date('2026-11-13T12:00:00+09:00') })
    expect(deadlineDDay('2026-11-13T11:59:00+09:00')).toBeNull()
    expect(deadlineDDay(null)).toBeNull()
  })
})

describe('formatDistance', () => {
  it.each([
    [null, ''],
    [0.4, '1km 이내'],
    [3.4, '약 3km'],
    [1234.5, '약 1,235km'],
  ])('%s → %s', (km, expected) => {
    expect(formatDistance(km)).toBe(expected)
  })
})

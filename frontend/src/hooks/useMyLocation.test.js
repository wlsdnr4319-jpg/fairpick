import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as geo from '../utils/location'
import { useMyLocation } from './useMyLocation'

const KEY = 'fairpick.nearby'
const SEOUL = { lat: 37.51, lng: 127.06 }

describe('useMyLocation', () => {
  // 실제 브라우저 위치 대신 정해 둔 결과를 돌려준다.
  // 중괄호 필수: beforeEach 가 함수를 돌려주면 Vitest 는 그걸 정리 함수로 보고 테스트 뒤에 호출한다
  beforeEach(() => {
    vi.spyOn(geo, 'getCoarseLocation').mockResolvedValue(SEOUL)
  })

  it('처음에는 위치를 묻지 않는다 (버튼을 눌러야 묻는다)', () => {
    const { result } = renderHook(() => useMyLocation())
    expect(result.current.location).toBeNull()
    expect(geo.getCoarseLocation).not.toHaveBeenCalled()
  })

  it('locate 를 부르면 위치를 받아 온다', async () => {
    const { result } = renderHook(() => useMyLocation())
    await act(() => result.current.locate())
    expect(result.current.location).toEqual(SEOUL)
    expect(result.current.loading).toBe(false)
  })

  it('기본은 기억하지 않는다 (목록 화면은 위치를 URL 에만 둔다)', async () => {
    const { result } = renderHook(() => useMyLocation())
    await act(() => result.current.locate())
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('remember 면 이 탭(sessionStorage)에 기억했다가 다시 쓴다', async () => {
    const first = renderHook(() => useMyLocation({ remember: true }))
    await act(() => first.result.current.locate())
    expect(JSON.parse(sessionStorage.getItem(KEY))).toEqual(SEOUL)

    const again = renderHook(() => useMyLocation({ remember: true }))
    expect(again.result.current.location).toEqual(SEOUL)
  })

  it('위치 지우기는 기억한 값도 지운다', async () => {
    sessionStorage.setItem(KEY, JSON.stringify(SEOUL))
    const { result } = renderHook(() => useMyLocation({ remember: true }))
    act(() => result.current.clear())
    expect(result.current.location).toBeNull()
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('저장된 값이 깨져 있으면 무시한다', () => {
    sessionStorage.setItem(KEY, '{"lat":"서울"}')
    const { result } = renderHook(() => useMyLocation({ remember: true }))
    expect(result.current.location).toBeNull()
  })

  it('실패하면 에러 문구를 보여 주고 null 을 돌려준다', async () => {
    geo.getCoarseLocation.mockRejectedValue(new Error('위치 권한이 꺼져 있어요.'))
    const { result } = renderHook(() => useMyLocation())
    let found
    await act(async () => {
      found = await result.current.locate()
    })
    expect(found).toBeNull()
    expect(result.current.error).toBe('위치 권한이 꺼져 있어요.')
  })
})

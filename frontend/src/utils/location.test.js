import { afterEach, describe, expect, it, vi } from 'vitest'
import { getCoarseLocation, roundCoord } from './location'

const PERMISSION_DENIED = 1

function mockGeolocation(impl) {
  vi.stubGlobal('navigator', { geolocation: { getCurrentPosition: vi.fn(impl) } })
}

afterEach(() => vi.unstubAllGlobals())

describe('roundCoord', () => {
  it('소수 둘째 자리(약 1km)로 줄인다', () => {
    expect(roundCoord(37.51267)).toBe(37.51)
    expect(roundCoord(127.05896)).toBe(127.06)
  })
})

describe('getCoarseLocation', () => {
  it('정확한 좌표 대신 줄인 좌표를 돌려준다', async () => {
    mockGeolocation((ok) => ok({ coords: { latitude: 37.51267, longitude: 127.05896 } }))
    await expect(getCoarseLocation()).resolves.toEqual({ lat: 37.51, lng: 127.06 })
  })

  it('고정밀 위치는 요청하지 않는다', async () => {
    mockGeolocation((ok) => ok({ coords: { latitude: 0, longitude: 0 } }))
    await getCoarseLocation()
    const options = navigator.geolocation.getCurrentPosition.mock.calls[0][2]
    expect(options.enableHighAccuracy).toBe(false)
  })

  it('권한을 거부하면 설정 방법을 알려 준다', async () => {
    mockGeolocation((_ok, fail) => fail({ code: PERMISSION_DENIED, PERMISSION_DENIED }))
    await expect(getCoarseLocation()).rejects.toThrow('위치 권한이 꺼져 있어요')
  })

  it('그 밖의 실패는 다시 시도하라고 한다', async () => {
    mockGeolocation((_ok, fail) => fail({ code: 3, PERMISSION_DENIED }))
    await expect(getCoarseLocation()).rejects.toThrow('잠시 후 다시 시도')
  })

  it('위치 기능이 없는 브라우저', async () => {
    vi.stubGlobal('navigator', {})
    await expect(getCoarseLocation()).rejects.toThrow('지원하지 않아요')
  })
})

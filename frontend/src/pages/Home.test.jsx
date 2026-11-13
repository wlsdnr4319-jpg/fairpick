import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { makeFair, page } from '../test/fixtures'
import { currentLocation, renderPage } from '../test/render'
import { API, json, server } from '../test/server'
import { getCoarseLocation } from '../utils/location'
import Home from './Home'

// 브라우저 위치 권한 대신 결과만 정한다
vi.mock('../utils/location', async (importOriginal) => ({ ...(await importOriginal()), getCoarseLocation: vi.fn() }))

const HOUR = 3_600_000
const DAY = 24 * HOUR
const at = (ms) => new Date(Date.now() + ms).toISOString()

// 홈의 세 구역은 같은 /fairs 를 다른 조건으로 부른다. 조건에 맞는 목록을 돌려주고 요청을 기록한다
function fairsBy({ weekend = [], deadline = [], nearby = [] } = {}) {
  const requests = []
  server.use(
    http.get(`${API}/fairs`, ({ request }) => {
      const params = Object.fromEntries(new URL(request.url).searchParams)
      requests.push(params)
      if (params.period === 'this_weekend') return json(page(weekend))
      if (params.sort === 'prereg_deadline') return json(page(deadline))
      if (params.sort === 'distance') return json(page(nearby))
      return json(page([]))
    }),
  )
  return requests
}

const renderHome = () => renderPage(<Home />)
const section = (title) => screen.getByRole('heading', { name: title, level: 2 }).closest('section')

beforeEach(() => {
  getCoarseLocation.mockReset()
})

describe('홈 검색', () => {
  it('검색어를 목록 화면의 q 로 넘긴다 (앞뒤 공백 제거)', async () => {
    fairsBy()
    renderHome()
    await userEvent.type(screen.getByLabelText('박람회 검색'), '  커피 {Enter}')
    await waitFor(() => expect(currentLocation(screen)).toBe(`/fairs?q=${encodeURIComponent('커피')}`))
  })

  it('비워 두고 검색하면 전체 목록', async () => {
    fairsBy()
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: '검색' }))
    await waitFor(() => expect(currentLocation(screen)).toBe('/fairs'))
  })

  it('카테고리 바로가기', async () => {
    fairsBy()
    server.use(http.get(`${API}/categories`, () => json([{ code: 'pet', name: '반려동물' }])))
    renderHome()
    expect(await screen.findByRole('link', { name: '반려동물' })).toHaveAttribute('href', '/fairs?category=pet')
    expect(screen.getByRole('link', { name: '#무료' })).toHaveAttribute('href', '/fairs?free=true')
  })
})

describe('이번 주말', () => {
  it('이번 주말 박람회를 보여 주고 전체 보기로 이어진다', async () => {
    fairsBy({ weekend: [makeFair({ title: '주말 커피 페어' })] })
    renderHome()
    const weekend = section('이번 주말 갈 만한 박람회')
    expect(await within(weekend).findByRole('heading', { name: '주말 커피 페어' })).toBeInTheDocument()
    expect(within(weekend).getByRole('link', { name: '전체 보기' })).toHaveAttribute('href', '/fairs?period=this_weekend')
  })

  it('없으면 안내', async () => {
    fairsBy()
    renderHome()
    expect(await screen.findByText('이번 주말에 열리는 박람회가 없어요')).toBeInTheDocument()
  })
})

describe('내 주변', () => {
  it('누르기 전에는 위치를 묻지 않고, 목록 요청도 하지 않는다', async () => {
    const requests = fairsBy()
    renderHome()
    await screen.findByText('이번 주말에 열리는 박람회가 없어요')
    expect(getCoarseLocation).not.toHaveBeenCalled()
    expect(requests.some((p) => p.sort === 'distance')).toBe(false)
    expect(within(section('내 주변 박람회')).queryByRole('link', { name: '전체 보기' })).not.toBeInTheDocument()
  })

  it('위치를 받으면 50km 안을 거리순으로 받고, 끝난 행사는 뺀다', async () => {
    getCoarseLocation.mockResolvedValue({ lat: 37.51, lng: 127.06 })
    const requests = fairsBy({
      nearby: [
        makeFair({ title: '가까운 박람회', distance_km: 0.4 }),
        makeFair({ title: '이미 끝난 박람회', progress: 'ended', distance_km: 1.2 }),
      ],
    })
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: '내 위치로 찾기' }))

    const nearby = section('내 주변 박람회')
    expect(await within(nearby).findByRole('heading', { name: '가까운 박람회' })).toBeInTheDocument()
    expect(within(nearby).queryByRole('heading', { name: '이미 끝난 박람회' })).not.toBeInTheDocument()
    expect(requests.find((p) => p.sort === 'distance')).toMatchObject({ lat: '37.51', lng: '127.06', radius_km: '50' })
    expect(within(nearby).getByRole('link', { name: '전체 보기' })).toHaveAttribute(
      'href',
      '/fairs?lat=37.51&lng=127.06&sort=distance&radius_km=50',
    )
  })

  it('이 탭에서 받은 위치를 기억해 다시 와도 바로 보여 주고, 지우면 잊는다', async () => {
    sessionStorage.setItem('fairpick.nearby', JSON.stringify({ lat: 37.51, lng: 127.06 }))
    fairsBy({ nearby: [makeFair({ title: '가까운 박람회' })] })
    renderHome()
    expect(await screen.findByRole('heading', { name: '가까운 박람회' })).toBeInTheDocument()
    expect(getCoarseLocation).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: '위치 지우기' }))
    expect(screen.getByRole('button', { name: '내 위치로 찾기' })).toBeInTheDocument()
    expect(sessionStorage.getItem('fairpick.nearby')).toBeNull()
  })

  it('끝난 행사만 있으면 비어 있다고 안내', async () => {
    getCoarseLocation.mockResolvedValue({ lat: 37.51, lng: 127.06 })
    fairsBy({ nearby: [makeFair({ progress: 'ended' })] })
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: '내 위치로 찾기' }))
    expect(await screen.findByText('50km 안에서 열릴 박람회가 없어요')).toBeInTheDocument()
  })

  it('위치 권한이 꺼져 있으면 켜는 방법을 알려 준다', async () => {
    getCoarseLocation.mockRejectedValue(new Error('위치 권한이 꺼져 있어요. 브라우저 주소창의 사이트 설정에서 위치를 허용해 주세요.'))
    fairsBy()
    renderHome()
    await userEvent.click(screen.getByRole('button', { name: '내 위치로 찾기' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('위치 권한이 꺼져 있어요')
    expect(screen.getByRole('button', { name: '내 위치로 찾기' })).toBeEnabled()
  })
})

describe('사전등록 마감 임박', () => {
  it('남은 날을 D-n, 오늘 마감은 "오늘", 이미 지난 마감은 "마감"으로', async () => {
    fairsBy({
      deadline: [
        makeFair({ id: 101, title: '사흘 남음', prereg_end_at: at(3 * DAY + 2 * HOUR) }),
        makeFair({ id: 102, title: '오늘 마감', prereg_end_at: at(2 * HOUR) }),
        // 목록을 받은 뒤 마감 시각이 지난 경우 ('D-null' 로 보이던 문제)
        makeFair({ id: 103, title: '방금 마감', prereg_end_at: at(-HOUR) }),
      ],
    })
    renderHome()
    const rows = await within(section('사전등록 마감 임박')).findAllByRole('link', { name: /마감$/ })
    expect(rows.map((r) => r.firstChild.textContent)).toEqual(['D-3', '오늘', '마감'])
    expect(rows[0]).toHaveAttribute('href', '/fairs/101')
  })
})

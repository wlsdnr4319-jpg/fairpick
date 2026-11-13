import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { renderPage } from '../test/render'
import { API, json, server } from '../test/server'
import Report from './Report'

// 차트(recharts)의 ResponsiveContainer 가 쓰는 브라우저 기능. jsdom 에는 없다.
// 차트 그림 자체는 E2E 로 보고, 여기서는 숫자로 쓴 문장과 표를 본다
beforeAll(() => {
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  )
})

const CATEGORIES = [
  { code: 'food', name: '식음료', count: 12, avg_days: 3.5, free_ratio: 0.25 },
  { code: 'pet', name: '반려동물', count: 0, avg_days: 0, free_ratio: 0 },
]

const month = (m, byCategory) => ({
  month: `2026-${String(m).padStart(2, '0')}`,
  total: Object.values(byCategory).reduce((a, b) => a + b, 0),
  by_category: byCategory,
})

const HISTORY = {
  from_year: 2019,
  to_year: 2025,
  total: 60,
  venues: ['코엑스', '킨텍스'],
  venue_since: { 코엑스: 2019, 킨텍스: 2022 },
  by_year: [
    { year: 2019, total: 10, by_venue: { 코엑스: 10, 킨텍스: 0 } },
    { year: 2020, total: 2, by_venue: { 코엑스: 2, 킨텍스: 0 } },
    { year: 2025, total: 48, by_venue: { 코엑스: 18, 킨텍스: 30 } },
  ],
  themes: [
    { theme: '웨딩', total: 20, by_month: [0, 0, 8, 0, 0, 0, 0, 0, 0, 12, 0, 0], peak_months: [10] },
    { theme: '식음료', total: 6, by_month: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0], peak_months: [11] },
    { theme: '캠핑', total: 0, by_month: Array(12).fill(0), peak_months: [] },
  ],
  other_total: 3,
  excluded: { 입주박람회: 5 },
}

function statsEndpoints({ history = HISTORY } = {}) {
  const years = []
  server.use(
    http.get(`${API}/stats/overview`, () => json({ total: 30, free_ratio: 0.433, avg_days: 3.2 })),
    http.get(`${API}/stats/monthly`, ({ request }) => {
      const year = new URL(request.url).searchParams.get('year')
      years.push(year)
      return json(year === '2026' ? [month(10, { food: 2 }), month(11, { food: 3, pet: 1 }), month(12, {})] : [month(1, {})])
    }),
    http.get(`${API}/stats/categories`, () => json(CATEGORIES)),
    http.get(`${API}/stats/venues`, () => json([{ venue: '코엑스', region: '서울', count: 20, top_category: '식음료' }])),
    http.get(`${API}/stats/history`, () => json(history)),
  )
  return years
}

const section = (name) => screen.getByRole('heading', { name }).closest('section')

describe('통계 리포트', () => {
  it('요약 숫자', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    const kpi = await screen.findByRole('region', { name: '요약' })
    expect(kpi).toHaveTextContent('30개')
    expect(kpi).toHaveTextContent('43%')
    expect(kpi).toHaveTextContent('3.2일')
  })

  it('월별: 가장 많은 달을 문장으로 알려 주고, 표로 보면 쓰인 카테고리만 열로', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    expect(await screen.findByText('11월에 가장 많이 열렸어요 (4개)')).toBeInTheDocument()

    await userEvent.click(within(section('2026년 월별 개최 수')).getByRole('button', { name: '표로 보기' }))
    const table = within(section('2026년 월별 개최 수')).getByRole('table')
    expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['월', '식음료', '반려동물', '합계'])
    expect(within(table).getAllByRole('row')[2]).toHaveTextContent('11월314')
  })

  it('연도를 바꾸면 그 해를 받고, 데이터가 없으면 그렇게 말한다', async () => {
    const years = statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    await screen.findByText('11월에 가장 많이 열렸어요 (4개)')
    await userEvent.selectOptions(screen.getByLabelText('연도'), '2027')
    expect(await screen.findByRole('heading', { name: '2027년 월별 개최 수' })).toBeInTheDocument()
    expect(await screen.findByText('이 해의 데이터가 없어요')).toBeInTheDocument()
    expect(years).toEqual(['2026', '2027'])
  })

  it('카테고리: 열리지 않은 카테고리는 평균 기간·무료 비율을 - 로', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    expect(await screen.findByText('식음료 박람회가 가장 많아요')).toBeInTheDocument()
    const rows = within(section('카테고리별 개최 수')).getAllByRole('row')
    expect(rows[1]).toHaveTextContent('식음료123.5일25%')
    expect(rows[2]).toHaveTextContent('반려동물0--')
  })

  it('전시장: 가장 많이 열리는 곳과 그곳의 주력 카테고리', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    expect(await screen.findByText('코엑스에서 가장 많이 열려요. 가장 많은 카테고리: 식음료')).toBeInTheDocument()
  })

  it('지난 기록: 중간에 기록이 시작된 전시장은 해마다 비교에서 빼고 그 사실을 알린다', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    expect(await screen.findByRole('heading', { name: '지난 7년의 박람회 (2019~2025)' })).toBeInTheDocument()
    // 킨텍스(2022~)를 더하면 2025년이 늘어난 것처럼 보이므로 코엑스만으로 비교
    expect(screen.getByText('1곳 기준 가장 적은 해는 2020년(2개), 가장 많은 해는 2025년(18개)이에요')).toBeInTheDocument()
    expect(screen.getByText(/킨텍스는 2022년부터 공식 일정 기록이 있어요/)).toBeInTheDocument()
  })

  it('주제별 달: 많이 열린 달, 개최가 없는 주제는 빼고, 뺀 행사 수를 밝힌다', async () => {
    statsEndpoints()
    renderPage(<Report />, { path: '/report' })
    expect(await screen.findByText('웨딩은 10월, 식음료는 11월에 가장 많이 열렸어요')).toBeInTheDocument()
    const heat = screen.getByRole('table', { name: /주제와 달별 개최 수/ })
    expect(within(heat).getByRole('rowheader', { name: '웨딩' })).toBeInTheDocument()
    expect(within(heat).queryByRole('rowheader', { name: '캠핑' })).not.toBeInTheDocument()
    expect(within(heat).getByTitle('웨딩 · 10월: 12개 (7년 합계)')).toHaveTextContent('12')
    expect(screen.getByText('제목 키워드로 나눴고, 입주박람회 5건 · 주제를 못 찾은 3건은 뺐어요')).toBeInTheDocument()
  })

  it('지난 기록이 없으면 그 구역을 그리지 않는다', async () => {
    statsEndpoints({ history: { ...HISTORY, total: 0 } })
    renderPage(<Report />, { path: '/report' })
    await screen.findByText('식음료 박람회가 가장 많아요')
    await waitFor(() => expect(screen.queryByText(/지난 \d+년의 박람회/)).not.toBeInTheDocument())
  })
})

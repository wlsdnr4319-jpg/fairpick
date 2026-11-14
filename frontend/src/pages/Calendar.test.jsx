import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { currentLocation, renderPage } from '../test/render'
import { API, json, server } from '../test/server'
import { shortTitle } from '../utils/format'
import Calendar from './Calendar'

// 캘린더 API 응답 모양 (backend/app/schemas/engagement.py 의 CalendarItem)
const item = (id, title, start_date, end_date, scale = 1) => ({
  id,
  title,
  start_date,
  end_date,
  category: 'food',
  category_name: '식음료',
  venue: '코엑스',
  region: '서울',
  hall: 'A홀',
  bookmark_count: 0,
  scale,
})

// 달마다 정해 둔 목록을 돌려주고, 요청한 달을 기록한다
function calendarOf(byMonth = {}) {
  const months = []
  server.use(
    http.get(`${API}/fairs/calendar`, ({ request }) => {
      const month = new URL(request.url).searchParams.get('month')
      months.push(month)
      return json(byMonth[month] ?? [])
    }),
  )
  return months
}

const renderCalendar = (route = '/calendar?month=2026-11') => renderPage(<Calendar />, { path: '/calendar', route })
const dayButton = (name) => screen.findByRole('button', { name })
const panel = () => screen.getByRole('region', { name: /박람회 \d+개/ })
// 달력 칸에 짧게 나온 행사 (패널의 링크와 구분)
const inCells = (id) => document.querySelectorAll(`[data-fair="${id}"]`)

describe('캘린더', () => {
  it('주소의 달을 그리고 그 달만 요청한다', async () => {
    const months = calendarOf()
    renderCalendar()
    expect(screen.getByRole('heading', { name: '2026년 11월' })).toBeInTheDocument()
    await waitFor(() => expect(months).toEqual(['2026-11']))
    // 2026-11-01 은 일요일이라 빈 칸 없이 1일부터, 30일까지
    expect(await dayButton('11월 1일, 박람회 0개')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '11월 30일, 박람회 0개' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^11월 31일/ })).not.toBeInTheDocument()
  })

  it('주소에 달이 없으면 이번 달', async () => {
    const months = calendarOf()
    renderCalendar('/calendar')
    const now = new Date()
    expect(screen.getByRole('heading', { name: `${now.getFullYear()}년 ${now.getMonth() + 1}월` })).toBeInTheDocument()
    await waitFor(() => expect(months).toHaveLength(1))
    expect(screen.queryByRole('button', { name: '오늘' })).not.toBeInTheDocument() // 이미 이번 달
  })

  it('여러 날 열리는 박람회는 기간의 모든 날 칸에, 앞 달에 시작했으면 이 달 부분만', async () => {
    calendarOf({
      '2026-11': [item(1, '제25회 서울카페쇼', '2026-11-19', '2026-11-22'), item(2, '가을 리빙페어', '2026-10-30', '2026-11-02')],
    })
    renderCalendar()
    await waitFor(() => expect(inCells(1)).toHaveLength(4))
    expect(inCells(1)[0]).toHaveTextContent(/^서울카페쇼$/) // 칸에는 회차를 뗀 짧은 이름
    expect(inCells(2)).toHaveLength(2) // 11월 1~2일
  })

  it('칸에는 규모가 큰 행사 2개만, 나머지는 +n', async () => {
    calendarOf({
      '2026-11': [
        item(1, '작은 행사', '2026-11-14', '2026-11-14', 2),
        item(2, '가장 큰 행사', '2026-11-14', '2026-11-14', 20),
        item(3, '중간 행사', '2026-11-14', '2026-11-14', 9),
        item(4, '더 작은 행사', '2026-11-14', '2026-11-14', 1),
      ],
    })
    renderCalendar()
    const cell = await dayButton('11월 14일, 박람회 4개')
    await waitFor(() => expect(inCells(2)).toHaveLength(1))
    expect(inCells(3)).toHaveLength(1)
    expect(inCells(1)).toHaveLength(0)
    expect(within(cell).getByText('+2')).toBeInTheDocument()
  })

  it('날짜를 누르면 옆 상자에 그날 행사가 큰 순서로 모두 나오고, 고른 날은 주소에 남는다', async () => {
    calendarOf({
      '2026-12': [
        item(1, '서울카페쇼', '2026-12-03', '2026-12-05', 5),
        { ...item(2, '리빙페어', '2026-12-05', '2026-12-05', 12), hall: '전관', bookmark_count: 3 },
        item(3, '다른 날 행사', '2026-12-20', '2026-12-20'),
      ],
    })
    renderCalendar('/calendar?month=2026-12')

    // 이번 달이 아니면 행사가 있는 첫날(3일)이 골라져 있다
    expect(await screen.findByRole('heading', { name: '12월 3일 (목) · 박람회 1개' })).toBeInTheDocument()

    const day5 = await dayButton('12월 5일, 박람회 2개')
    await userEvent.click(day5)
    expect(day5).toHaveAttribute('aria-pressed', 'true')
    expect(currentLocation(screen)).toBe('/calendar?month=2026-12&day=5')
    expect(screen.getByRole('heading', { name: '12월 5일 (토) · 박람회 2개' })).toBeInTheDocument()

    const links = within(panel()).getAllByRole('link')
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/fairs/2', '/fairs/1']) // 큰 행사 먼저
    expect(links[0]).toHaveTextContent('리빙페어')
    expect(links[0]).toHaveTextContent('코엑스 전관 · 서울')
    expect(links[0]).toHaveTextContent('북마크 3')
    expect(within(panel()).queryByText('다른 날 행사')).not.toBeInTheDocument()
  })

  it('행사가 없는 날을 고르면 없다고 알려 준다', async () => {
    calendarOf({ '2026-11': [item(1, '서울카페쇼', '2026-11-19', '2026-11-22')] })
    renderCalendar('/calendar?month=2026-11&day=2')
    expect(await screen.findByRole('heading', { name: '11월 2일 (월) · 박람회 0개' })).toBeInTheDocument()
    expect(screen.getByText('이 날 열리는 박람회가 없어요')).toBeInTheDocument()
  })

  it('다음 달로 넘기면 해가 바뀌고 주소에 남는다', async () => {
    const months = calendarOf({ '2027-01': [item(9, '신년 웨딩박람회', '2027-01-09', '2027-01-10')] })
    renderCalendar('/calendar?month=2026-12')
    await userEvent.click(screen.getByRole('button', { name: '다음 달' }))
    expect(screen.getByRole('heading', { name: '2027년 1월' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/calendar?month=2027-01')
    await waitFor(() => expect(inCells(9)).toHaveLength(2))
    expect(months).toContain('2027-01')
    // 다른 달에서는 '오늘' 버튼으로 이번 달로 돌아간다
    await userEvent.click(screen.getByRole('button', { name: '오늘' }))
    expect(currentLocation(screen)).toBe('/calendar')
  })

  it('이전 달로 넘기면 해가 거꾸로 바뀐다', async () => {
    calendarOf()
    renderCalendar('/calendar?month=2026-01')
    await userEvent.click(screen.getByRole('button', { name: '이전 달' }))
    expect(screen.getByRole('heading', { name: '2025년 12월' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/calendar?month=2025-12')
  })
})

describe('칸에 들어갈 짧은 이름', () => {
  it.each([
    ['제25회 서울카페쇼', '서울카페쇼'],
    ['2026 대구 캠페어', '대구 캠페어'],
    ['메가푸드쇼 2026', '메가푸드쇼'],
    ['제 3 회 코믹월드', '코믹월드'],
    ['메가쇼 2026 시즌 2', '메가쇼 2026 시즌 2'],
    ['2026 푸드위크 코리아(제21회 서울국제식품산업전)', '푸드위크 코리아'],
    ['2026', '2026'], // 다 지워지면 원래 이름
  ])('%s → %s', (title, short) => {
    expect(shortTitle(title)).toBe(short)
  })
})

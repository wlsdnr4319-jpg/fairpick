import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { currentLocation, renderPage } from '../test/render'
import { API, json, server } from '../test/server'
import Calendar from './Calendar'

// 캘린더 API 응답 모양 (backend/app/schemas/engagement.py 의 CalendarItem)
const item = (id, title, start_date, end_date) => ({ id, title, start_date, end_date, venue: '코엑스', category: 'food' })

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
const linksTo = (title) => screen.queryAllByRole('link', { name: title })

describe('캘린더', () => {
  it('주소의 달을 그리고 그 달만 요청한다', async () => {
    const months = calendarOf()
    renderCalendar()
    expect(screen.getByRole('heading', { name: '2026년 11월' })).toBeInTheDocument()
    await waitFor(() => expect(months).toEqual(['2026-11']))
    // 2026-11-01 은 일요일이라 빈 칸 없이 1일부터, 30일까지
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.queryByText('31')).not.toBeInTheDocument()
  })

  it('주소에 달이 없으면 이번 달', async () => {
    const months = calendarOf()
    renderCalendar('/calendar')
    const now = new Date()
    expect(screen.getByRole('heading', { name: `${now.getFullYear()}년 ${now.getMonth() + 1}월` })).toBeInTheDocument()
    await waitFor(() => expect(months).toHaveLength(1))
  })

  it('여러 날 열리는 박람회는 기간의 모든 날에, 앞 달에 시작했으면 이 달 부분만', async () => {
    calendarOf({
      '2026-11': [item(1, '서울카페쇼', '2026-11-19', '2026-11-22'), item(2, '가을 리빙페어', '2026-10-30', '2026-11-02')],
    })
    renderCalendar()
    await waitFor(() => expect(linksTo('서울카페쇼')).toHaveLength(4))
    expect(linksTo('서울카페쇼')[0]).toHaveAttribute('href', '/fairs/1')
    expect(linksTo('서울카페쇼')[0]).toHaveAttribute('title', '서울카페쇼 · 코엑스')
    expect(linksTo('가을 리빙페어')).toHaveLength(2) // 11월 1~2일
  })

  it('하루에 셋보다 많으면 셋만 보이고 나머지는 +n', async () => {
    calendarOf({ '2026-11': [1, 2, 3, 4, 5].map((n) => item(n, `토요일 행사 ${n}`, '2026-11-14', '2026-11-14')) })
    renderCalendar()
    expect(await screen.findByText('+2')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /토요일 행사/ })).toHaveLength(3)
  })

  it('다음 달로 넘기면 해가 바뀌고 주소에 남는다', async () => {
    const months = calendarOf({ '2027-01': [item(9, '신년 웨딩박람회', '2027-01-09', '2027-01-10')] })
    renderCalendar('/calendar?month=2026-12')
    await userEvent.click(screen.getByRole('button', { name: '다음 달' }))
    expect(screen.getByRole('heading', { name: '2027년 1월' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/calendar?month=2027-01')
    expect(await screen.findAllByRole('link', { name: '신년 웨딩박람회' })).toHaveLength(2)
    expect(months).toContain('2027-01')
  })

  it('이전 달로 넘기면 해가 거꾸로 바뀐다', async () => {
    calendarOf()
    renderCalendar('/calendar?month=2026-01')
    await userEvent.click(screen.getByRole('button', { name: '이전 달' }))
    expect(screen.getByRole('heading', { name: '2025년 12월' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/calendar?month=2025-12')
  })
})

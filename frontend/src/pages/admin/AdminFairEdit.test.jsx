import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { Route } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { currentLocation, renderApp } from '../../test/render'
import { API, apiError, json, server } from '../../test/server'
import AdminFairEdit from './AdminFairEdit'

const routes = (
  <>
    <Route path="/admin/fairs/new" element={<AdminFairEdit />} />
    <Route path="/admin/fairs/:fairId/edit" element={<AdminFairEdit />} />
  </>
)

// 저장 요청 본문을 기록하고, 받은 값에 id 를 붙여 돌려주는 가짜 관리자 API
function adminEndpoints(existing) {
  const sent = []
  server.use(
    http.post(`${API}/admin/fairs`, async ({ request }) => {
      const body = await request.json()
      sent.push(body)
      return json({ ...body, id: 41, source: 'manual', verified_at: null }, 201)
    }),
    http.patch(`${API}/admin/fairs/:id`, async ({ request, params }) => {
      const body = await request.json()
      sent.push(body)
      return json({ ...existing, ...body, id: Number(params.id) })
    }),
    http.get(`${API}/admin/fairs/:id`, () => json(existing)),
  )
  return sent
}

beforeEach(() => {
  server.use(
    http.get(`${API}/categories`, () => json([{ code: 'food', name: '식음료' }])),
    http.get(`${API}/venues`, () => json([{ id: 3, name: '코엑스', region: '서울' }])),
    http.get(`${API}/tags`, () => json([{ slug: 'date', name: '데이트 추천' }])),
  )
})

async function fillRequired(user) {
  await user.type(screen.getByLabelText('제목'), '새 박람회')
  await user.selectOptions(await screen.findByLabelText('카테고리'), await screen.findByRole('option', { name: '식음료' }))
  await user.selectOptions(screen.getByLabelText('전시장'), await screen.findByRole('option', { name: '코엑스 (서울)' }))
  await user.type(screen.getByLabelText('시작일'), '2027-05-01')
  await user.type(screen.getByLabelText('종료일'), '2027-05-03')
}

describe('관리자 박람회 등록', () => {
  it('빈 칸은 null(모름)로, 입장료 0 은 무료로, 일시는 한국 시간(+09:00)으로 보낸다', async () => {
    const sent = adminEndpoints()
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/new' })
    await fillRequired(user)
    await user.type(screen.getByLabelText(/현장 입장료/), '0')
    await user.type(screen.getByLabelText('사전등록 마감 (한국 시간)'), '2027-04-30T23:59')
    await user.click(screen.getByLabelText('데이트 추천'))
    await user.click(screen.getByRole('button', { name: '저장' }))

    await screen.findByRole('heading', { name: '박람회 수정' })
    expect(sent[0]).toMatchObject({
      title: '새 박람회',
      category: 'food',
      venue_id: 3,
      start_date: '2027-05-01',
      end_date: '2027-05-03',
      price_onsite: 0,
      price_prereg: null,
      prereg_end_at: '2027-04-30T23:59:00+09:00',
      prereg_start_at: null,
      hall: null,
      summary: null,
      official_url: null,
      tags: ['date'],
      status: 'draft',
      verified: false,
    })
  })

  it('등록하면 수정 화면으로 옮겨도 "저장했어요" 를 보여 준다', async () => {
    // 수정 화면으로 옮기며 폼을 새로 그려서 안내가 사라지던 문제 (E2E 로 발견)
    adminEndpoints({ id: 41, title: '새 박람회', category: 'food', venue_id: 3, start_date: '2027-05-01', end_date: '2027-05-03', status: 'draft', tags: [] })
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/new' })
    await fillRequired(user)
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByRole('heading', { name: '박람회 수정' })).toBeInTheDocument()
    expect(currentLocation(screen)).toBe('/admin/fairs/41/edit')
    expect(screen.getByRole('status')).toHaveTextContent('저장했어요')
  })

  it('서버가 거부하면 그 이유를 보여 주고 머문다', async () => {
    server.use(http.post(`${API}/admin/fairs`, () => apiError(422, 'INVALID_PERIOD', '종료일이 시작일보다 빨라요')))
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/new' })
    await fillRequired(user)
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByRole('status')).toHaveTextContent('종료일이 시작일보다 빨라요')
    expect(currentLocation(screen)).toBe('/admin/fairs/new')
  })
})

describe('관리자 박람회 수정', () => {
  const existing = {
    id: 7,
    title: '서울커피엑스포',
    category: 'food',
    venue_id: 3,
    hall: 'A홀',
    start_date: '2027-04-15',
    end_date: '2027-04-18',
    price_onsite: 15000,
    price_prereg: null,
    prereg_end_at: '2027-04-10T18:00:00+09:00',
    status: 'published',
    tags: ['date'],
    verified_at: '2026-11-04T14:00:00+09:00',
  }

  it('저장된 값을 폼에 채우고, 정보 확인 체크는 매번 새로 하게 비워 둔다', async () => {
    adminEndpoints(existing)
    renderApp(routes, { route: '/admin/fairs/7/edit' })

    expect(await screen.findByLabelText('제목')).toHaveValue('서울커피엑스포')
    expect(screen.getByLabelText('사전등록 마감 (한국 시간)')).toHaveValue('2027-04-10T18:00')
    expect(screen.getByLabelText(/현장 입장료/)).toHaveValue(15000)
    expect(await screen.findByLabelText('데이트 추천')).toBeChecked()
    expect(screen.getByLabelText(/공식 사이트에서 정보를 확인했어요/)).not.toBeChecked()
    expect(screen.getByText('마지막 정보 확인: 2026-11-04 14:00')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '공개 화면 보기' })).toHaveAttribute('href', '/fairs/7')
  })

  it('수정은 PATCH 로 보내고 같은 화면에 머문다', async () => {
    const sent = adminEndpoints(existing)
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/7/edit' })
    await user.selectOptions(await screen.findByLabelText('상태'), 'hidden')
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByRole('status')).toHaveTextContent('저장했어요')
    expect(sent[0]).toMatchObject({ status: 'hidden', price_onsite: 15000, hall: 'A홀' })
    expect(currentLocation(screen)).toBe('/admin/fairs/7/edit')
    // 숨김으로 바꾸면 공개 화면 링크는 사라진다
    expect(screen.queryByRole('link', { name: '공개 화면 보기' })).not.toBeInTheDocument()
  })
})

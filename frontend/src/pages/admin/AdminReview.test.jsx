import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderPage } from '../../test/render'
import { API, json, server } from '../../test/server'
import AdminReview from './AdminReview'

// 검수 큐 항목 (backend/app/schemas/crawl.py 의 CrawledItemOut)
function crawledItem(overrides = {}) {
  return {
    id: 11,
    source: 'coex',
    external_id: 'E1',
    raw_title: '디저트 페어',
    raw_period: '2027.03.05 ~ 2027.03.07',
    raw_venue: '코엑스 C홀',
    detail_url: 'https://www.coex.co.kr/e/1',
    raw_payload: { extra: { hall: 'C홀' } },
    parsed_start_date: '2027-03-05',
    parsed_end_date: '2027-03-07',
    parsed_venue_id: 3,
    parsed_venue_name: '코엑스',
    change_status: 'new',
    fair_id: null,
    merge_candidates: [],
    ...overrides,
  }
}

// 큐를 돌려주고, 승인·병합·반려 요청을 기록한다
function reviewQueue(items) {
  const actions = []
  server.use(
    http.get(`${API}/admin/crawled-items`, () => json({ items, page: 1, size: 50, total: items.length })),
    http.get(`${API}/admin/crawl-sources`, () => json([])),
    http.post(`${API}/admin/crawled-items/:id/:kind`, async ({ request, params }) => {
      const text = await request.text()
      actions.push({ id: Number(params.id), kind: params.kind, body: text ? JSON.parse(text) : undefined })
      return json({ id: 99 })
    }),
  )
  return actions
}

beforeEach(() => {
  server.use(
    http.get(`${API}/categories`, () => json([{ code: 'food', name: '식음료' }])),
    http.get(`${API}/tags`, () => json([{ slug: 'date', name: '데이트 추천' }])),
  )
})

const renderReview = () => renderPage(<AdminReview />, { path: '/admin/review' })

describe('수집 검수', () => {
  it('원본과 정규화 결과를 나란히 보여 준다', async () => {
    reviewQueue([crawledItem()])
    renderReview()
    expect(await screen.findByRole('heading', { name: '수집 검수 (1)' })).toBeInTheDocument()
    const item = screen.getByRole('listitem')
    expect(item).toHaveTextContent('2027.03.05 ~ 2027.03.07')
    expect(item).toHaveTextContent('기간: 2027-03-05 ~ 2027-03-07')
    expect(item).toHaveTextContent('장소: 코엑스')
  })

  it('카테고리를 고르기 전에는 승인할 수 없고, 승인하면 채운 정보로 박람회를 만든다', async () => {
    const actions = reviewQueue([crawledItem()])
    const user = userEvent.setup()
    renderReview()
    await user.click(await screen.findByRole('button', { name: '정보 채우고 승인' }))

    const approve = screen.getByRole('button', { name: '승인해 공개' })
    expect(approve).toBeDisabled()

    await user.selectOptions(screen.getByLabelText('카테고리'), await screen.findByRole('option', { name: '식음료' }))
    await user.selectOptions(screen.getByLabelText('일반인 관람'), 'public')
    await user.type(screen.getByPlaceholderText('현장 입장료(원)'), '5000')
    await user.click(approve)

    await waitFor(() => expect(actions).toHaveLength(1))
    expect(actions[0]).toMatchObject({
      id: 11,
      kind: 'approve',
      body: {
        title: '디저트 페어',
        category: 'food',
        venue_id: 3,
        hall: 'C홀', // 원본의 전시홀
        start_date: '2027-03-05',
        end_date: '2027-03-07',
        public_access: 'public',
        price_onsite: 5000,
        price_prereg: null,
        official_url: 'https://www.coex.co.kr/e/1',
        status: 'published',
        verified: true,
      },
    })
  })

  it('장소를 찾지 못한 항목은 알려 주고 승인할 수 없다 (반려만 가능)', async () => {
    reviewQueue([crawledItem({ parsed_venue_id: null, parsed_venue_name: null, parsed_start_date: null, parsed_end_date: null })])
    const user = userEvent.setup()
    renderReview()
    const item = await screen.findByRole('listitem')
    expect(item).toHaveTextContent('매칭 실패')
    expect(item).toHaveTextContent('읽지 못함 (직접 입력)')

    await user.click(within(item).getByRole('button', { name: '정보 채우고 승인' }))
    await user.selectOptions(within(item).getByLabelText('카테고리'), await screen.findByRole('option', { name: '식음료' }))
    expect(within(item).getByRole('button', { name: '승인해 공개' })).toBeDisabled()
    expect(within(item).getByRole('button', { name: '반려' })).toBeEnabled()
  })

  it('이미 박람회와 연결된 변경 항목은 본문 없이 변경 확인만 보낸다', async () => {
    const actions = reviewQueue([crawledItem({ change_status: 'changed', fair_id: 5 })])
    const user = userEvent.setup()
    renderReview()
    const item = await screen.findByRole('listitem')
    expect(item).toHaveTextContent('변경됨')
    expect(within(item).getByRole('link', { name: '#5' })).toHaveAttribute('href', '/admin/fairs/5/edit')

    await user.click(within(item).getByRole('button', { name: '변경 확인' }))
    await waitFor(() => expect(actions).toEqual([{ id: 11, kind: 'approve', body: undefined }]))
  })

  it('병합 후보를 고르면 그 박람회로 병합한다', async () => {
    const actions = reviewQueue([
      crawledItem({ merge_candidates: [{ fair_id: 8, title: '디저트페어 2027', start_date: '2027-03-05', end_date: '2027-03-07', similarity: 0.82 }] }),
    ])
    const user = userEvent.setup()
    renderReview()
    expect(await screen.findByText(/디저트페어 2027 \(2027-03-05\) · 유사도 0.82/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '병합' }))
    await waitFor(() => expect(actions).toEqual([{ id: 11, kind: 'merge', body: { fair_id: 8 } }]))
  })

  it('반려', async () => {
    const actions = reviewQueue([crawledItem()])
    renderReview()
    await userEvent.click(await screen.findByRole('button', { name: '반려' }))
    await waitFor(() => expect(actions).toEqual([{ id: 11, kind: 'reject', body: undefined }]))
  })

  it('큐가 비면 안내', async () => {
    reviewQueue([])
    renderReview()
    expect(await screen.findByText('검수할 항목이 없어요')).toBeInTheDocument()
  })
})

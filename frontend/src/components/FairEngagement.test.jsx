import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { renderPage } from '../test/render'
import { API, json, loggedInAs, server } from '../test/server'
import { MyVisit, Reviews, TagVotes } from './FairEngagement'

const FAIR_ID = 7
const renderOnFair = (element) => renderPage(element, { path: '/fairs/:fairId', route: `/fairs/${FAIR_ID}` })

// 관람 노트 API. 저장·삭제를 기록하고 내 노트 목록을 그에 맞게 바꾼다
function visitEndpoints(initial = []) {
  let visits = initial
  const calls = []
  server.use(
    http.get(`${API}/me/visits`, () => json(visits)),
    http.post(`${API}/fairs/:fairId/visits`, async ({ request, params }) => {
      const body = await request.json()
      calls.push({ method: 'POST', body })
      const visit = { id: 501, fair_id: Number(params.fairId), ...body }
      visits = [visit]
      return json(visit, 201)
    }),
    http.patch(`${API}/visits/:id`, async ({ request }) => {
      const body = await request.json()
      calls.push({ method: 'PATCH', body })
      visits = [{ ...visits[0], ...body }]
      return json(visits[0])
    }),
    http.delete(`${API}/visits/:id`, ({ params }) => {
      calls.push({ method: 'DELETE', id: Number(params.id) })
      visits = []
      return new Response(null, { status: 204 })
    }),
    http.get(`${API}/fairs/:fairId/reviews`, () => json({ items: [], page: 1, size: 10, total: 0, rating_avg: null, rating_count: 0 })),
  )
  return calls
}

const myNote = { id: 501, fair_id: FAIR_ID, visited_on: '2026-11-12', rating: 4, memo: '주차장이 붐벼요', is_public: false }

describe('관람 노트', () => {
  it('비로그인이면 로그인 안내만 (돌아올 주소 포함)', async () => {
    renderOnFair(<MyVisit fairId={FAIR_ID} />)
    expect(await screen.findByRole('link', { name: '로그인하고 관람 노트 남기기' })).toHaveAttribute('href', '/login?next=%2Ffairs%2F7')
  })

  it('처음 남기면 POST, 빈 칸은 null, 별점은 숫자로', async () => {
    loggedInAs()
    const calls = visitEndpoints()
    const user = userEvent.setup()
    renderOnFair(<MyVisit fairId={FAIR_ID} />)
    await user.click(await screen.findByRole('button', { name: '다녀왔어요' }))
    await user.selectOptions(screen.getByLabelText('별점'), '5')
    await user.click(screen.getByLabelText(/후기로 공개하기/))
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByText('날짜 미입력 · ★★★★★ · 공개')).toBeInTheDocument()
    expect(calls).toEqual([{ method: 'POST', body: { visited_on: null, rating: 5, memo: null, is_public: true } }])
  })

  it('이미 있으면 고치기로 PATCH 하고, 저장된 값이 폼에 채워져 있다', async () => {
    loggedInAs()
    const calls = visitEndpoints([myNote])
    const user = userEvent.setup()
    renderOnFair(<MyVisit fairId={FAIR_ID} />)
    expect(await screen.findByText('2026-11-12 · ★★★★ · 나만 보기')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '고치기' }))
    expect(screen.getByLabelText('다녀온 날')).toHaveValue('2026-11-12')
    expect(screen.getByLabelText('별점')).toHaveValue('4')
    await user.clear(screen.getByPlaceholderText(/다녀온 기록/))
    await user.type(screen.getByPlaceholderText(/다녀온 기록/), '오전이 한산해요')
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(await screen.findByText('오전이 한산해요')).toBeInTheDocument()
    expect(calls[0]).toMatchObject({ method: 'PATCH', body: { memo: '오전이 한산해요', rating: 4 } })
  })

  it('지우면 폼을 닫고 처음 상태로 돌아간다', async () => {
    // 지운 뒤에도 고치기 폼이 열린 채 남던 문제 (E2E 로 발견)
    loggedInAs()
    const calls = visitEndpoints([myNote])
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    renderOnFair(<MyVisit fairId={FAIR_ID} />)
    await user.click(await screen.findByRole('button', { name: '고치기' }))
    await user.click(screen.getByRole('button', { name: '삭제' }))

    expect(await screen.findByRole('button', { name: '다녀왔어요' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '저장' })).not.toBeInTheDocument()
    expect(calls).toEqual([{ method: 'DELETE', id: 501 }])
  })

  it('삭제 확인 창에서 취소하면 지우지 않는다', async () => {
    loggedInAs()
    const calls = visitEndpoints([myNote])
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    renderOnFair(<MyVisit fairId={FAIR_ID} />)
    await user.click(await screen.findByRole('button', { name: '고치기' }))
    await user.click(screen.getByRole('button', { name: '삭제' }))
    expect(calls).toEqual([])
  })
})

describe('후기', () => {
  const review = { id: 9, nickname: '다른사람', is_mine: false, rating: 5, visited_on: '2026-11-11', memo: '라테 시음이 좋았어요', like_count: 2, liked_by_me: false }

  function reviewEndpoints(items = [review]) {
    const likes = []
    server.use(
      http.get(`${API}/fairs/:fairId/reviews`, () => json({ items, page: 1, size: 10, total: items.length, rating_avg: 4.5, rating_count: 2 })),
      http.put(`${API}/visits/:id/like`, ({ params }) => {
        likes.push(Number(params.id))
        return json({})
      }),
    )
    return likes
  }

  it('평균 별점과 후기를 보여 주고, 비로그인은 좋아요를 누를 수 없다', async () => {
    reviewEndpoints()
    renderOnFair(<Reviews fairId={FAIR_ID} />)
    expect(await screen.findByRole('heading', { name: /후기 1개/ })).toHaveTextContent('★ 4.5 (2)')
    const item = screen.getByRole('listitem')
    expect(item).toHaveTextContent('라테 시음이 좋았어요')
    expect(within(item).getByRole('button', { name: '♥ 2' })).toBeDisabled()
  })

  it('로그인하면 좋아요를 보낸다', async () => {
    loggedInAs()
    const likes = reviewEndpoints()
    renderOnFair(<Reviews fairId={FAIR_ID} />)
    const like = await screen.findByRole('button', { name: '♥ 2' })
    await waitFor(() => expect(like).toBeEnabled())
    await userEvent.click(like)
    await waitFor(() => expect(likes).toEqual([9]))
  })
})

describe('태그 투표', () => {
  it('투표할 태그가 없으면 아무것도 그리지 않는다', async () => {
    server.use(http.get(`${API}/fairs/:fairId/tag-votes`, () => json([])))
    const { container } = renderOnFair(<TagVotes fairId={FAIR_ID} />)
    await waitFor(() => expect(container.querySelector('section')).toBeNull())
  })

  it('비로그인은 누를 수 없고 로그인 안내를 보여 준다', async () => {
    server.use(http.get(`${API}/fairs/:fairId/tag-votes`, () => json([{ tag_id: 2, name: '이색', vote_count: 1, voted: false }])))
    renderOnFair(<TagVotes fairId={FAIR_ID} />)
    expect(await screen.findByRole('button', { name: '#이색 1' })).toBeDisabled()
    expect(screen.getByRole('link', { name: '로그인하고 투표하기' })).toBeInTheDocument()
  })

  it('누르면 서버가 돌려준 표 수로 바뀐다', async () => {
    loggedInAs()
    let rows = [{ tag_id: 2, name: '이색', vote_count: 1, voted: false }]
    server.use(
      http.get(`${API}/fairs/:fairId/tag-votes`, () => json(rows)),
      http.put(`${API}/fairs/:fairId/tag-votes/:tagId`, () => {
        rows = [{ ...rows[0], vote_count: 2, voted: true }]
        return json(rows)
      }),
    )
    renderOnFair(<TagVotes fairId={FAIR_ID} />)
    const tag = await screen.findByRole('button', { name: '#이색 1' })
    await waitFor(() => expect(tag).toBeEnabled())
    await userEvent.click(tag)
    expect(await screen.findByRole('button', { name: '#이색 2' })).toHaveAttribute('aria-pressed', 'true')
  })
})

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { makeFair, page } from '../test/fixtures'
import { currentLocation, renderPage } from '../test/render'
import { API, apiError, json, loggedInAs, server } from '../test/server'
import FairList from './FairList'

// 목록 API 가 받은 쿼리스트링을 기록한다
function listEndpoint(response) {
  const queries = []
  server.use(
    http.get(`${API}/fairs`, ({ request }) => {
      queries.push(Object.fromEntries(new URL(request.url).searchParams))
      return typeof response === 'function' ? response(request) : json(response)
    }),
  )
  return queries
}

const renderList = (route = '/fairs') => renderPage(<FairList />, { path: '/fairs', route })

describe('박람회 목록', () => {
  it('목록과 개수를 보여 준다', async () => {
    listEndpoint(page([makeFair({ title: '서울 커피 엑스포' }), makeFair({ title: '펫쇼' })], { total: 2 }))
    renderList()
    expect(await screen.findByText('서울 커피 엑스포')).toBeInTheDocument()
    expect(screen.getByText('펫쇼')).toBeInTheDocument()
    expect(screen.getByText('2개')).toBeInTheDocument()
  })

  it('URL 의 필터를 그대로 API 에 보낸다 (주소를 공유하면 같은 목록)', async () => {
    const queries = listEndpoint(page([]))
    renderList('/fairs?category=food&tags=date,kids&free=true&page=2')
    await screen.findByText('0개')
    expect(queries.at(-1)).toEqual({ category: 'food', tags: 'date,kids', free: 'true', page: '2' })
  })

  it('위치 없이 거리순인 주소는 오류 대신 기본 정렬로 요청한다', async () => {
    const queries = listEndpoint(page([]))
    renderList('/fairs?sort=distance&radius_km=10&q=커피')
    await screen.findByText('0개')
    expect(queries.at(-1)).toEqual({ q: '커피' })
  })

  it('필터를 바꾸면 URL 에 반영하고 1페이지로 돌아간다', async () => {
    server.use(http.get(`${API}/categories`, () => json([{ code: 'food', name: '식음료' }])))
    listEndpoint(page([]))
    renderList('/fairs?page=3')
    await screen.findByRole('option', { name: '식음료' })

    await userEvent.selectOptions(screen.getByLabelText('카테고리'), 'food')

    expect(currentLocation(screen)).toBe('/fairs?category=food')
  })

  it('검색어는 앞뒤 공백을 빼고 URL 에 넣는다', async () => {
    listEndpoint(page([]))
    renderList()
    await userEvent.type(screen.getByLabelText('검색어'), '  디저트  {Enter}')
    expect(currentLocation(screen)).toBe('/fairs?q=%EB%94%94%EC%A0%80%ED%8A%B8')
  })

  it('결과가 없으면 필터 초기화 버튼', async () => {
    listEndpoint(page([]))
    renderList('/fairs?free=true')
    await userEvent.click(await screen.findByRole('button', { name: '필터 초기화' }))
    expect(currentLocation(screen)).toBe('/fairs')
  })

  it('API 오류면 서버 문구와 다시 시도 버튼', async () => {
    let fail = true
    listEndpoint(() => (fail ? apiError(500, 'INTERNAL', '서버에 문제가 생겼어요') : json(page([makeFair({ title: '복구됨' })]))))
    renderList()
    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 문제가 생겼어요')

    fail = false
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(await screen.findByText('복구됨')).toBeInTheDocument()
  })
})

describe('목록에서 북마크', () => {
  const card = (title) => screen.getByText(title).closest('a')

  it('비로그인이면 지금 주소를 붙여 로그인 화면으로 보낸다', async () => {
    listEndpoint(page([makeFair({ title: '커피 엑스포' })]))
    renderList('/fairs?category=food')
    await screen.findByText('커피 엑스포')

    await userEvent.click(within(card('커피 엑스포')).getByRole('button', { name: '북마크' }))

    expect(currentLocation(screen)).toBe('/login?next=%2Ffairs%3Fcategory%3Dfood')
  })

  it('응답을 기다리지 않고 바로 표시한다 (낙관적 업데이트)', async () => {
    loggedInAs()
    const fair = makeFair({ title: '커피 엑스포' })
    listEndpoint(page([fair]))
    let release
    server.use(http.put(`${API}/fairs/${fair.id}/bookmark`, () => new Promise((r) => (release = () => r(json({}))))))
    renderList()
    await screen.findByText('커피 엑스포')

    await userEvent.click(within(card('커피 엑스포')).getByRole('button', { name: '북마크' }))

    // 서버가 아직 답하지 않았는데 이미 눌린 상태
    expect(within(card('커피 엑스포')).getByRole('button', { name: '북마크 해제' })).toHaveAttribute('aria-pressed', 'true')
    release()
  })

  it('요청이 실패하면 원래대로 되돌린다', async () => {
    loggedInAs()
    const fair = makeFair({ title: '커피 엑스포' })
    listEndpoint(page([fair]))
    server.use(http.put(`${API}/fairs/${fair.id}/bookmark`, () => apiError(500, 'INTERNAL')))
    renderList()
    await screen.findByText('커피 엑스포')

    await userEvent.click(within(card('커피 엑스포')).getByRole('button', { name: '북마크' }))

    await waitFor(() =>
      expect(within(card('커피 엑스포')).getByRole('button', { name: '북마크' })).toHaveAttribute('aria-pressed', 'false'),
    )
  })

  it('새로고침 직후 로그인 복구가 늦게 끝나도 북마크 여부를 다시 받아 온다', async () => {
    // 목록은 토큰이 있을 때만 북마크 여부를 알려 준다. 복구(refresh)는 목록보다 늦게 끝난다
    let restore
    server.use(
      http.post(`${API}/auth/refresh`, () => new Promise((r) => (restore = () => r(json({ access_token: 'a', user: { id: 1, nickname: '나', role: 'user' } }))))),
      http.get(`${API}/fairs`, ({ request }) =>
        json(page([makeFair({ id: 77, title: '커피 엑스포', is_bookmarked: request.headers.has('Authorization') })])),
      ),
    )
    renderList()
    await screen.findByText('커피 엑스포')
    expect(within(card('커피 엑스포')).getByRole('button', { name: '북마크' })).toHaveAttribute('aria-pressed', 'false')

    restore()

    expect(await within(card('커피 엑스포')).findByRole('button', { name: '북마크 해제' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('첫 목록 응답이 오기 전에 로그인 복구가 끝나도 토큰을 붙여 다시 받는다', async () => {
    // 순서: 목록 요청(토큰 없음) 시작 → 복구 끝 → 토큰 없는 목록 응답 도착
    let restore
    let releaseAnonymous
    server.use(
      http.post(`${API}/auth/refresh`, () => new Promise((r) => (restore = () => r(json({ access_token: 'a', user: { id: 1, nickname: '나', role: 'user' } }))))),
      http.get(`${API}/fairs`, ({ request }) => {
        const authed = request.headers.has('Authorization')
        const body = json(page([makeFair({ id: 78, title: '느린 목록', is_bookmarked: authed })]))
        return authed ? body : new Promise((r) => (releaseAnonymous = () => r(body)))
      }),
    )
    renderList()
    await waitFor(() => expect(releaseAnonymous).toBeTypeOf('function'))

    restore()
    await new Promise((r) => setTimeout(r, 50)) // 복구 처리가 끝날 시간
    releaseAnonymous()

    await screen.findByText('느린 목록')
    expect(await within(card('느린 목록')).findByRole('button', { name: '북마크 해제' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('북마크 해제는 DELETE 로 보낸다', async () => {
    loggedInAs()
    const fair = makeFair({ title: '커피 엑스포', is_bookmarked: true })
    listEndpoint(page([fair]))
    let deleted = false
    server.use(
      http.delete(`${API}/fairs/${fair.id}/bookmark`, () => {
        deleted = true
        return new Response(null, { status: 204 })
      }),
    )
    renderList()
    await screen.findByText('커피 엑스포')

    await userEvent.click(within(card('커피 엑스포')).getByRole('button', { name: '북마크 해제' }))

    await waitFor(() => expect(deleted).toBe(true))
  })
})

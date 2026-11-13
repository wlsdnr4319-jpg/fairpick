import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from '../store/AuthContext'

/* eslint-disable react-refresh/only-export-components -- 테스트 도우미라 빠른 새로고침과 상관없다 */

// 지금 주소를 화면에 적어 둔다. 테스트에서 이동·쿼리스트링을 확인할 때 쓴다
function LocationProbe() {
  const location = useLocation()
  // output 요소는 role=status 라 화면의 안내 문구와 겹친다. 의미 없는 span 으로 둔다
  return <span data-testid="location">{location.pathname + location.search}</span>
}

// 앱과 같은 공급자(Query·Router·Auth)로 감싸 그린다. 재시도는 꺼서 실패가 바로 보이게 한다
export function renderApp(routes, { route = '/' } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <Routes>{routes}</Routes>
          <LocationProbe />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...utils, queryClient }
}

// 하나의 화면만 그릴 때
export function renderPage(element, { path = '/', route = path } = {}) {
  return renderApp(
    <>
      <Route path={path} element={element} />
      <Route path="*" element={<p>다른 화면</p>} />
    </>,
    { route },
  )
}

export const currentLocation = (screen) => screen.getByTestId('location').textContent

import { Link, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-white text-gray-900">
      <header className="border-b border-gray-200">
        <div className="mx-auto flex h-14 max-w-5xl items-center px-4">
          <Link to="/" className="text-lg font-bold text-indigo-600">
            페어픽
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      {/* 정보 정확성 안내 (레퍼런스 15장 공개 전 체크리스트). 처리방침·약관 링크는 8주차에 추가 */}
      <footer className="border-t border-gray-200 py-6 text-center text-xs text-gray-500">
        일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.
      </footer>
    </div>
  )
}

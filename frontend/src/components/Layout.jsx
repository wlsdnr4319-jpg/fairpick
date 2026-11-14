import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'

// 둘러보기 메뉴: 데스크톱은 한 줄, 휴대폰은 헤더 아래 둘째 줄 (전에는 휴대폰에서 캘린더·통계가 아예 숨겨져 갈 방법이 없었다)
const BROWSE = [
  ['/fairs', '박람회 찾기'],
  ['/calendar', '캘린더'],
  ['/report', '통계'],
]

export default function Layout() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const nav = ({ isActive }) =>
    `inline-flex min-h-11 shrink-0 items-center rounded-md px-2 text-sm ${
      isActive ? 'font-semibold text-indigo-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`
  const browse = BROWSE.map(([to, label]) => (
    <NavLink key={to} to={to} className={nav}>
      {label}
    </NavLink>
  ))

  return (
    <div className="flex min-h-screen flex-col bg-white text-gray-900">
      {/* 키보드 사용자가 메뉴를 건너뛰고 본문으로 바로 가는 링크. 포커스를 받을 때만 보인다 */}
      <a
        href="#main"
        className="sr-only z-20 rounded-lg bg-indigo-600 px-4 py-2 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-3"
      >
        본문으로 건너뛰기
      </a>
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-1 px-4">
          <Link to="/" translate="no" className="mr-auto rounded-md text-lg font-bold text-indigo-600">
            페어픽
          </Link>
          <nav aria-label="둘러보기" className="hidden items-center gap-1 sm:flex">
            {browse}
          </nav>
          {ready && user && (
            <>
              <NavLink to="/mypage" className={nav}>
                북마크
              </NavLink>
              {user.role === 'admin' && (
                <NavLink to="/admin" className={nav}>
                  관리자
                </NavLink>
              )}
              <button
                type="button"
                className="inline-flex min-h-11 items-center rounded-md px-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                onClick={async () => {
                  await logout()
                  navigate('/')
                }}
              >
                로그아웃
              </button>
            </>
          )}
          {ready && !user && (
            <NavLink to="/login" className={nav}>
              로그인
            </NavLink>
          )}
        </div>
        <nav aria-label="둘러보기" className="-mt-1 flex gap-1 overflow-x-auto px-3 pb-1 sm:hidden">
          {browse}
        </nav>
      </header>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 outline-none">
        <Outlet />
      </main>

      {/* 정보 정확성 안내와 법적 고지 (레퍼런스 15장) */}
      <footer className="border-t border-gray-200 py-6 text-center text-xs text-gray-500">
        <p>일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.</p>
        <p className="mt-2 space-x-3">
          <Link to="/privacy" className="font-semibold underline hover:text-gray-800">
            개인정보 처리방침
          </Link>
          <Link to="/terms" className="underline hover:text-gray-800">
            이용약관
          </Link>
          <a href="mailto:contact@example.com" className="underline hover:text-gray-800">
            정보 수정·삭제 요청
          </a>
        </p>
      </footer>
    </div>
  )
}

import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'

export default function Layout() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const nav = ({ isActive }) => `px-2 py-2 text-sm ${isActive ? 'text-indigo-700 font-semibold' : 'text-gray-600'}`

  return (
    <div className="flex min-h-screen flex-col bg-white text-gray-900">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
          <Link to="/" className="mr-auto text-lg font-bold text-indigo-600">
            페어픽
          </Link>
          <NavLink to="/fairs" className={nav}>
            박람회 찾기
          </NavLink>
          <NavLink to="/calendar" className={(s) => `${nav(s)} hidden sm:inline`}>
            캘린더
          </NavLink>
          <NavLink to="/report" className={(s) => `${nav(s)} hidden sm:inline`}>
            통계
          </NavLink>
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
                className="px-2 py-2 text-sm text-gray-600"
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
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      {/* 정보 정확성 안내와 법적 고지 (레퍼런스 15장) */}
      <footer className="border-t border-gray-200 py-6 text-center text-xs text-gray-500">
        <p>일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.</p>
        <p className="mt-2 space-x-3">
          <Link to="/privacy" className="font-semibold underline">
            개인정보 처리방침
          </Link>
          <Link to="/terms" className="underline">
            이용약관
          </Link>
          <a href="mailto:contact@example.com" className="underline">
            정보 수정·삭제 요청
          </a>
        </p>
      </footer>
    </div>
  )
}

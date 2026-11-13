import { Navigate, Outlet, useLocation, useSearchParams } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'
import { safeNext } from '../utils/nav'

function Waiting() {
  return <p className="py-16 text-center text-gray-400">확인 중…</p>
}

// 로그인이 안 된 상태에서 보호된 화면에 오면 갈 곳.
// 직접 로그아웃·탈퇴했다면 홈으로 (로그아웃 버튼의 navigate('/') 와 같은 곳이라 경쟁하지 않는다.
// React Router 7 은 주소 변경을 transition 으로 처리해서, 사용자 상태가 먼저 바뀌면 이 가드가 먼저 그려진다).
// 그 밖에는 로그인 화면으로 보내고, 로그인 후 원래 페이지로 돌아온다 (레퍼런스 11장)
function LoginRedirect({ signedOut, location }) {
  if (signedOut) return <Navigate to="/" replace />
  return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
}

export function ProtectedRoute() {
  const { user, ready, signedOut } = useAuth()
  const location = useLocation()
  if (!ready) return <Waiting />
  if (!user) return <LoginRedirect signedOut={signedOut} location={location} />
  return <Outlet />
}

export function AdminRoute() {
  const { user, ready, signedOut } = useAuth()
  const location = useLocation()
  if (!ready) return <Waiting />
  if (!user) return <LoginRedirect signedOut={signedOut} location={location} />
  if (user.role !== 'admin') return <p className="py-16 text-center text-gray-600">관리자만 이용할 수 있어요</p>
  return <Outlet />
}

// 로그인·가입 화면은 비로그인만. 로그인에 성공하는 순간에도 이 가드가 먼저 다시 그려지므로
// 홈이 아니라 next 로 보낸다. 홈으로 보내면 로그인 화면의 navigate(next) 와 경쟁해 가끔 홈에 떨어진다 (E2E 로 발견)
export function GuestOnlyRoute() {
  const { user, ready } = useAuth()
  const [params] = useSearchParams()
  if (!ready) return <Waiting />
  if (user) return <Navigate to={safeNext(params.get('next'))} replace />
  return <Outlet />
}

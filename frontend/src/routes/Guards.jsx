import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'

function Waiting() {
  return <p className="py-16 text-center text-gray-400">확인 중…</p>
}

// 비로그인이면 로그인 화면으로 보내고, 로그인 후 원래 페이지로 돌아온다 (레퍼런스 11장)
export function ProtectedRoute() {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Waiting />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return <Outlet />
}

export function AdminRoute() {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Waiting />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (user.role !== 'admin') return <p className="py-16 text-center text-gray-600">관리자만 이용할 수 있어요</p>
  return <Outlet />
}

export function GuestOnlyRoute() {
  const { user, ready } = useAuth()
  if (!ready) return <Waiting />
  if (user) return <Navigate to="/" replace />
  return <Outlet />
}

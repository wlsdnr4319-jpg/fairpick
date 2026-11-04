import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { NEXT_KEY } from '../components/SocialButtons'
import { useAuth } from '../store/AuthContext'
import { safeNext } from '../utils/nav'

// 소셜 로그인 후 서버가 보내는 화면. 서버가 리프레시 쿠키를 심었으므로,
// 앱 시작 때의 로그인 복구(/auth/refresh)가 끝나면 로그인 상태가 된다. 토큰은 주소에 실려 오지 않는다.
export default function OAuthCallback() {
  const { user, ready } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!ready) return
    if (!user) {
      navigate('/login?oauth_error=OAUTH_FAILED', { replace: true })
      return
    }
    let next = '/'
    try {
      next = sessionStorage.getItem(NEXT_KEY) ?? '/'
      sessionStorage.removeItem(NEXT_KEY)
    } catch {
      // 저장소를 못 쓰면 홈으로
    }
    navigate(safeNext(next), { replace: true })
  }, [ready, user, navigate])

  return <p className="py-16 text-center text-gray-400">로그인하는 중…</p>
}

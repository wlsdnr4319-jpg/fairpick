import { useLocation, useNavigate } from 'react-router-dom'
import { useBookmark } from '../hooks/useFairs'
import { useAuth } from '../store/AuthContext'

export default function BookmarkButton({ fairId, bookmarked, className = '' }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const mutation = useBookmark(fairId)

  const onClick = (e) => {
    e.preventDefault() // 카드 링크 이동을 막는다
    e.stopPropagation()
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(location.pathname + location.search)}`)
      return
    }
    mutation.mutate(!bookmarked)
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={bookmarked ? '북마크 해제' : '북마크'}
      aria-pressed={bookmarked}
      className={`inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/90 shadow ${className}`}
    >
      <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
        <path
          d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"
          fill={bookmarked ? '#4f46e5' : 'none'}
          stroke="#4f46e5"
          strokeWidth="2"
        />
      </svg>
    </button>
  )
}

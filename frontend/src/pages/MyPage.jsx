import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchMyBookmarks, withdraw } from '../api/auth'
import { errorMessage } from '../api/client'
import FairCard from '../components/FairCard'
import Pagination from '../components/Pagination'
import { EmptyState, ErrorState, SkeletonGrid } from '../components/States'
import { useAuth } from '../store/AuthContext'

// 마이페이지: 북마크 모아보기 (F-07)
export default function MyPage() {
  const { user } = useAuth()
  const [page, setPage] = useState(1)
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['bookmarks', page],
    queryFn: () => fetchMyBookmarks(page),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{user.nickname}님의 북마크</h1>
        <Link to="/mypage/settings" className="text-sm text-gray-600 underline">
          계정 설정
        </Link>
      </div>
      {isPending && <SkeletonGrid count={3} />}
      {isError && <ErrorState onRetry={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState
          title="아직 북마크한 박람회가 없어요"
          action={
            <Link to="/fairs" className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-white">
              박람회 둘러보기
            </Link>
          }
        />
      )}
      {data && data.items.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((f) => (
              <FairCard key={f.id} fair={f} />
            ))}
          </div>
          <Pagination page={data.page} size={data.size} total={data.total} onChange={setPage} />
        </>
      )}
    </div>
  )
}

export function Settings() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  const onWithdraw = async () => {
    if (!window.confirm('탈퇴하면 이메일, 닉네임, 북마크가 모두 지워지고 되돌릴 수 없어요. 탈퇴할까요?')) return
    try {
      await withdraw()
      setUser(null)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">계정 설정</h1>
      <dl className="space-y-2 rounded-xl border p-4 text-sm">
        <div className="flex gap-4">
          <dt className="w-16 text-gray-500">이메일</dt>
          <dd>{user.email}</dd>
        </div>
        <div className="flex gap-4">
          <dt className="w-16 text-gray-500">닉네임</dt>
          <dd>{user.nickname}</dd>
        </div>
      </dl>
      <p className="text-sm text-gray-500">알림 설정은 다음 업데이트에서 제공돼요.</p>
      <section className="space-y-2 rounded-xl border border-red-200 p-4">
        <h2 className="font-semibold text-red-700">회원 탈퇴</h2>
        <p className="text-sm text-gray-600">이메일, 닉네임, 북마크가 바로 지워져요.</p>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button type="button" onClick={onWithdraw} className="min-h-11 rounded-lg border border-red-300 px-4 text-red-700">
          탈퇴하기
        </button>
      </section>
    </div>
  )
}

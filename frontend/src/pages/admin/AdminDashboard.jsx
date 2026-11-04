import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchAdminFairs } from '../../api/admin'
import { api } from '../../api/client'

function useCount(status) {
  return useQuery({
    queryKey: ['admin', 'count', status],
    queryFn: () => fetchAdminFairs({ status, size: 1 }).then((d) => d.total),
  })
}

function usePendingReview() {
  return useQuery({
    queryKey: ['admin', 'review-count'],
    queryFn: () => api.get('/admin/crawled-items', { params: { review_status: 'pending', size: 1 } }).then((r) => r.data.total),
    retry: false,
  })
}

export default function AdminDashboard() {
  const draft = useCount('draft')
  const published = useCount('published')
  const hidden = useCount('hidden')
  const review = usePendingReview()

  const cards = [
    ['검수 대기', review.data, '/admin/review'],
    ['초안', draft.data, '/admin/fairs?status=draft'],
    ['공개', published.data, '/admin/fairs?status=published'],
    ['숨김', hidden.data, '/admin/fairs?status=hidden'],
  ]
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">관리자</h1>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {cards.map(([label, value, to]) => (
          <Link key={label} to={to} className="rounded-xl border p-4 hover:bg-gray-50">
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-2xl font-bold">{value ?? '-'}</p>
          </Link>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <Link to="/admin/fairs/new" className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-white">
          새 박람회 등록
        </Link>
        <Link to="/admin/review" className="inline-flex min-h-11 items-center rounded-lg border px-4">
          수집 검수
        </Link>
        <Link to="/admin/crawl-runs" className="inline-flex min-h-11 items-center rounded-lg border px-4">
          수집 이력
        </Link>
        <button type="button" onClick={downloadExcel} className="inline-flex min-h-11 items-center rounded-lg border px-4">
          엑셀 내보내기
        </button>
      </div>
    </div>
  )
}

// 관리자 엑셀 내보내기 (F-23). 로그인 토큰이 필요해 링크 대신 API 로 받아 저장한다
async function downloadExcel() {
  const res = await api.get('/admin/export/fairs.xlsx', { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `fairpick-fairs-${new Date().toISOString().slice(0, 10)}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

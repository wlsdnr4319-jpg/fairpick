import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchAdminFairs } from '../../api/admin'
import Pagination from '../../components/Pagination'
import { ErrorState } from '../../components/States'
import { formatPeriod } from '../../utils/format'

const STATUS = { draft: '초안', published: '공개', hidden: '숨김' }

// 관리자 박람회 관리 목록 (F-08)
export default function AdminFairs() {
  const [params, setParams] = useSearchParams()
  const query = { status: params.get('status') ?? '', q: params.get('q') ?? '', page: params.get('page') ?? 1 }
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['admin', 'fairs', query],
    queryFn: () => fetchAdminFairs(query),
  })

  const set = (k, v) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v)
    else next.delete(k)
    if (k !== 'page') next.delete('page')
    setParams(next)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">박람회 관리</h1>
        <Link to="/admin/fairs/new" className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-white">
          새 박람회
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        {['', 'draft', 'published', 'hidden'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => set('status', s)}
            className={`min-h-11 rounded-lg px-4 text-sm ${query.status === s ? 'bg-gray-900 text-white' : 'border'}`}
          >
            {s ? STATUS[s] : '전체'}
          </button>
        ))}
        <input
          type="search"
          defaultValue={query.q}
          placeholder="제목 검색"
          aria-label="제목 검색"
          onKeyDown={(e) => e.key === 'Enter' && set('q', e.currentTarget.value.trim())}
          className="min-h-11 flex-1 rounded-lg border px-3"
        />
      </div>
      {isPending && <p className="text-gray-400">불러오는 중…</p>}
      {isError && <ErrorState onRetry={refetch} />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b text-gray-500">
                <tr>
                  <th className="py-2">상태</th>
                  <th>제목</th>
                  <th>기간</th>
                  <th>장소</th>
                  <th>정보 확인</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((f) => (
                  <tr key={f.id} className="border-b">
                    <td className="py-2">{STATUS[f.status]}</td>
                    <td>
                      <Link to={`/admin/fairs/${f.id}/edit`} className="text-indigo-700 underline">
                        {f.title}
                      </Link>
                    </td>
                    <td>{formatPeriod(f.start_date, f.end_date)}</td>
                    <td>{f.venue}</td>
                    <td>{f.verified_at ? f.verified_at.slice(0, 10) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} size={data.size} total={data.total} onChange={(p) => set('page', String(p))} />
        </>
      )}
    </div>
  )
}

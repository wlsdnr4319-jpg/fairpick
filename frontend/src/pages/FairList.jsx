import { Fragment } from 'react'
import { useSearchParams } from 'react-router-dom'
import FairCard from '../components/FairCard'
import FilterBar from '../components/FilterBar'
import Pagination from '../components/Pagination'
import { EmptyState, ErrorState, SkeletonGrid } from '../components/States'
import { useFairsFromUrl } from '../hooks/useFairs'
import { errorMessage } from '../api/client'

// 박람회 목록·필터 (레퍼런스 4장 /fairs, F-01·F-03·F-04)
export default function FairList() {
  const [params, setParams] = useSearchParams()
  const { data, isPending, isError, error, refetch, isPlaceholderData } = useFairsFromUrl()

  const goPage = (page) => {
    const next = new URLSearchParams(params)
    next.set('page', String(page))
    setParams(next)
    window.scrollTo({ top: 0 })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">박람회 찾기</h1>
      <FilterBar />

      {isPending && <SkeletonGrid />}
      {isError && <ErrorState message={errorMessage(error)} onRetry={refetch} />}
      {data && (
        <>
          <p className="text-sm text-gray-500" aria-live="polite">
            {data.total}개
          </p>
          {data.items.length === 0 ? (
            <EmptyState
              action={
                <button type="button" onClick={() => setParams({})} className="min-h-11 rounded-lg border px-4">
                  필터 초기화
                </button>
              }
            />
          ) : (
            <div aria-busy={isPlaceholderData || undefined} className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 ${isPlaceholderData ? 'opacity-60' : ''}`}>
              {data.items.map((f, i) => (
                <Fragment key={f.id}>
                  {/* API 가 끝난 행사를 맨 뒤로 보내므로, 처음 나오는 끝난 행사 앞에 구분 제목을 둔다 */}
                  {f.progress === 'ended' && data.items[i - 1]?.progress !== 'ended' && (
                    <h2 className="col-span-full mt-4 border-t pt-4 text-sm font-semibold text-gray-500">끝난 박람회</h2>
                  )}
                  <FairCard fair={f} />
                </Fragment>
              ))}
            </div>
          )}
          <Pagination page={data.page} size={data.size} total={data.total} onChange={goPage} />
        </>
      )}
    </div>
  )
}

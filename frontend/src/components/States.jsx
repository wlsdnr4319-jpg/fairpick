// 빈 화면, 에러, 로딩 (레퍼런스 4장 '빈 화면과 에러 화면')

export function EmptyState({ title = '조건에 맞는 박람회가 없어요', action }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 px-6 py-12 text-center">
      <p className="text-gray-600">{title}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ message = '정보를 불러오지 못했어요', onRetry }) {
  return (
    <div role="alert" className="rounded-xl bg-red-50 px-6 py-10 text-center text-red-700">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-4 min-h-11 rounded-lg border border-red-300 px-4">
          다시 시도
        </button>
      )}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="animate-pulse overflow-hidden rounded-xl border border-gray-200" aria-hidden="true">
      <div className="h-36 bg-gray-200" />
      <div className="space-y-2 p-4">
        <div className="h-4 w-3/4 rounded bg-gray-200" />
        <div className="h-3 w-1/2 rounded bg-gray-200" />
      </div>
    </div>
  )
}

export function SkeletonGrid({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

// 무한 스크롤 대신 페이지네이션 (레퍼런스 4장)
export default function Pagination({ page, size, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / size))
  if (pages <= 1) return null

  const start = Math.max(1, Math.min(page - 2, pages - 4))
  const nums = Array.from({ length: Math.min(5, pages) }, (_, i) => start + i)

  const btn = 'min-h-11 min-w-11 rounded-lg px-3 text-sm tabular-nums disabled:cursor-not-allowed disabled:opacity-40'
  return (
    <nav aria-label="페이지" className="flex items-center justify-center gap-1">
      <button type="button" className={`${btn} border enabled:hover:bg-gray-100`} disabled={page <= 1} onClick={() => onChange(page - 1)}>
        이전
      </button>
      {nums.map((n) => (
        <button
          key={n}
          type="button"
          aria-current={n === page ? 'page' : undefined}
          className={`${btn} ${n === page ? 'bg-indigo-600 text-white' : 'border hover:bg-gray-100'}`}
          onClick={() => onChange(n)}
        >
          {n}
        </button>
      ))}
      <button type="button" className={`${btn} border enabled:hover:bg-gray-100`} disabled={page >= pages} onClick={() => onChange(page + 1)}>
        다음
      </button>
    </nav>
  )
}

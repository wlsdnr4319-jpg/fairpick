import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TagChip } from '../components/Badges'
import FairCard from '../components/FairCard'
import { EmptyState, ErrorState, SkeletonCard } from '../components/States'
import { useCategories, useFairs } from '../hooks/useFairs'
import { useMyLocation } from '../hooks/useMyLocation'
import { deadlineDDay, formatDateTime } from '../utils/format'

// 홈 큐레이션 (레퍼런스 4장 홈 /, F-05)
export default function Home() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h1 className="text-2xl font-bold">이번 주말, 어떤 박람회 갈까요?</h1>
        <form
          role="search"
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            navigate(q.trim() ? `/fairs?q=${encodeURIComponent(q.trim())}` : '/fairs')
          }}
        >
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="커피, 일러스트, 캠핑…"
            aria-label="박람회 검색"
            className="min-h-11 flex-1 rounded-lg border border-gray-300 px-3"
          />
          <button type="submit" className="min-h-11 rounded-lg bg-indigo-600 px-4 text-white">
            검색
          </button>
        </form>
        <QuickLinks />
      </section>

      <WeekendSection />
      <NearbySection />
      <DeadlineSection />
    </div>
  )
}

function QuickLinks() {
  const { data: categories = [] } = useCategories()
  return (
    <div className="space-y-2">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {categories.map((c) => (
          <Link
            key={c.code}
            to={`/fairs?category=${c.code}`}
            className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-gray-100 px-4 text-sm hover:bg-indigo-50"
          >
            {c.name}
          </Link>
        ))}
      </div>
      <div className="flex flex-wrap gap-1.5">
        <TagChip asLink tag={{ slug: 'date', name: '데이트 추천' }} />
        <TagChip asLink tag={{ slug: 'unique', name: '이색' }} />
        <Link to="/fairs?free=true" className="inline-flex items-center rounded-full border border-gray-300 px-2.5 py-0.5 text-xs text-gray-600">
          #무료
        </Link>
      </div>
    </div>
  )
}

function Section({ title, more, children }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        {more && (
          <Link to={more} className="text-sm text-indigo-600">
            전체 보기
          </Link>
        )}
      </div>
      {children}
    </section>
  )
}

function WeekendSection() {
  const { data, isPending, isError, refetch } = useFairs({ period: 'this_weekend', size: 10 })
  return (
    <Section title="이번 주말 갈 만한 박람회" more="/fairs?period=this_weekend">
      {isPending && (
        <div className="flex gap-4 overflow-hidden">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {isError && <ErrorState onRetry={refetch} />}
      {data && data.items.length === 0 && <EmptyState title="이번 주말에 열리는 박람회가 없어요" />}
      {data && data.items.length > 0 && (
        <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-2">
          {data.items.map((f) => (
            <FairCard key={f.id} fair={f} compact />
          ))}
        </div>
      )}
    </Section>
  )
}

// 내 주변 박람회: 50km 안에서 진행 중·예정인 박람회를 가까운 순으로 (끝난 행사는 서버가 뒤로 보내므로 걸러내기만 한다)
const NEARBY_RADIUS_KM = 50

function NearbySection() {
  const { location, locate, clear, loading, error } = useMyLocation({ remember: true })
  const listUrl = location ? `/fairs?lat=${location.lat}&lng=${location.lng}&sort=distance&radius_km=${NEARBY_RADIUS_KM}` : null
  return (
    <Section title="내 주변 박람회" more={listUrl}>
      {!location ? (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/40 p-4">
          <p className="flex-1 text-sm text-gray-600">가까운 전시장에서 열리는 박람회를 거리순으로 보여드려요. 위치는 약 1km 단위로만 쓰고 저장하지 않아요.</p>
          <button type="button" onClick={locate} disabled={loading} className="min-h-11 rounded-lg bg-indigo-600 px-4 text-sm text-white disabled:opacity-60">
            {loading ? '위치 확인 중…' : '내 위치로 찾기'}
          </button>
          {error && (
            <p role="alert" className="w-full text-sm text-red-600">
              {error}
            </p>
          )}
        </div>
      ) : (
        <NearbyList location={location} onClear={clear} />
      )}
    </Section>
  )
}

function NearbyList({ location, onClear }) {
  const { data, isPending, isError, refetch } = useFairs({
    lat: location.lat,
    lng: location.lng,
    sort: 'distance',
    radius_km: NEARBY_RADIUS_KM,
    size: 10,
  })
  const items = (data?.items ?? []).filter((f) => f.progress !== 'ended')
  return (
    <div className="space-y-2">
      {isPending && (
        <div className="flex gap-4 overflow-hidden">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {isError && <ErrorState onRetry={refetch} />}
      {data && items.length === 0 && <EmptyState title={`${NEARBY_RADIUS_KM}km 안에서 열릴 박람회가 없어요`} />}
      {items.length > 0 && (
        <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-2">
          {items.map((f) => (
            <FairCard key={f.id} fair={f} compact />
          ))}
        </div>
      )}
      <button type="button" onClick={onClear} className="min-h-11 text-sm text-gray-500 underline">
        위치 지우기
      </button>
    </div>
  )
}

function DeadlineSection() {
  const { data, isPending, isError, refetch } = useFairs({ sort: 'prereg_deadline', size: 6 })
  return (
    <Section title="사전등록 마감 임박" more="/fairs?sort=prereg_deadline">
      {isPending && <SkeletonCard />}
      {isError && <ErrorState onRetry={refetch} />}
      {data && data.items.length === 0 && <EmptyState title="마감이 가까운 사전등록이 없어요" />}
      {data && data.items.length > 0 && (
        <ul className="divide-y rounded-xl border">
          {data.items.map((f) => {
            const d = deadlineDDay(f.prereg_end_at)
            return (
              <li key={f.id}>
                <Link to={`/fairs/${f.id}`} className="flex min-h-14 items-center gap-3 px-4 py-3 hover:bg-gray-50">
                  <span className="w-14 shrink-0 rounded-md bg-red-50 py-1 text-center text-sm font-bold text-red-600">
                    {d === 0 ? '오늘' : `D-${d}`}
                  </span>
                  <span className="flex-1 truncate">{f.title}</span>
                  <span className="text-xs text-gray-500">{formatDateTime(f.prereg_end_at)} 마감</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Section>
  )
}

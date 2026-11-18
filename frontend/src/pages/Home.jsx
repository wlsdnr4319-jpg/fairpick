import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
      {/* 홈 첫 화면: 전시장 안내판처럼 남색 바탕에 굵은 제목, 검색 버튼은 출입증 노랑 */}
      <section className="-mx-4 -mt-8 sm:mt-0 space-y-5 bg-indigo-700 px-5 py-8 text-white sm:mx-0 sm:rounded-3xl sm:px-8 sm:py-10">
        <h1 className="text-[2rem] leading-tight text-balance sm:text-5xl">
          이번 주말,{' '}
          <br />
          어떤 박람회 갈까요?
        </h1>
        <p className="max-w-xl text-sm text-indigo-100 sm:text-base">
          전시장 6곳 일정을 매일 모아 일반인 입장 여부, 입장료, 사전등록 마감까지 정리했어요.
        </p>
        <form
          role="search"
          className="flex max-w-xl gap-2"
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
            className="min-h-12 min-w-0 flex-1 rounded-xl border-0 bg-white px-4 text-gray-900 placeholder:text-gray-400 focus-visible:outline-amber-400"
          />
          <button
            type="submit"
            className="min-h-12 rounded-xl bg-amber-400 px-5 font-bold text-indigo-900 hover:bg-amber-300 focus-visible:outline-white"
          >
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
  const quick = 'inline-flex min-h-10 items-center rounded-full px-3.5 text-sm'
  return (
    // 휴대폰에서도 옆으로 밀지 않고 한눈에 보이게 줄바꿈한다
    <div className="flex flex-wrap gap-2">
      {categories.map((c) => (
        <Link
          key={c.code}
          to={`/fairs?category=${c.code}`}
          className={`${quick} bg-white/10 text-white hover:bg-white/20`}
        >
          {c.name}
        </Link>
      ))}
      <Link to="/fairs?tags=date" className={`${quick} border border-amber-400/70 text-amber-200 hover:bg-amber-400/10`}>
        #데이트 추천
      </Link>
      <Link to="/fairs?tags=unique" className={`${quick} border border-amber-400/70 text-amber-200 hover:bg-amber-400/10`}>
        #이색
      </Link>
      <Link to="/fairs?free=true" className={`${quick} border border-amber-400/70 text-amber-200 hover:bg-amber-400/10`}>
        #무료
      </Link>
    </div>
  )
}

// 카드 묶음. 예전에는 옆으로 미는 줄이었는데 휴대폰에서 다음 카드가 잘려 보여 세로로 쌓는다.
// 휴대폰은 처음 4개만(나머지는 '전체 보기'), 넓은 화면은 2~3열로 6개까지
function CardGrid({ fairs }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
      {fairs.slice(0, 6).map((f, i) => (
        <div key={f.id} className={i >= 4 ? 'hidden sm:block' : undefined}>
          <FairCard fair={f} />
        </div>
      ))}
    </div>
  )
}

function Section({ title, more, children }) {
  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-3">
        <h2 className="font-display text-2xl text-indigo-700">{title}</h2>
        {more && (
          <Link to={more} className="inline-flex min-h-10 items-center text-sm font-medium text-indigo-700 underline decoration-amber-400 decoration-2 underline-offset-4 hover:decoration-indigo-700">
            전체 보기
          </Link>
        )}
      </div>
      {children}
    </section>
  )
}

function WeekendSection() {
  const { data, isPending, isError, refetch } = useFairs({ period: 'this_weekend', size: 6 })
  return (
    <Section title="이번 주말 갈 만한 박람회" more="/fairs?period=this_weekend">
      {isPending && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {isError && <ErrorState onRetry={refetch} />}
      {data && data.items.length === 0 && <EmptyState title="이번 주말에 열리는 박람회가 없어요" />}
      {data && data.items.length > 0 && (
        <CardGrid fairs={data.items} />
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
        <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-indigo-50 p-4 sm:p-5">
          <p className="flex-1 text-sm text-gray-600">가까운 전시장에서 열리는 박람회를 거리순으로 보여드려요. 위치는 약 1km 단위로만 쓰고 저장하지 않아요.</p>
          <button type="button" onClick={locate} disabled={loading} className="min-h-11 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 text-sm text-white disabled:opacity-60">
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
    size: 6,
  })
  const items = (data?.items ?? []).filter((f) => f.progress !== 'ended')
  return (
    <div className="space-y-2">
      {isPending && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {isError && <ErrorState onRetry={refetch} />}
      {data && items.length === 0 && <EmptyState title={`${NEARBY_RADIUS_KM}km 안에서 열릴 박람회가 없어요`} />}
      {items.length > 0 && (
        <CardGrid fairs={items} />
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
        <ul className="divide-y rounded-2xl border">
          {data.items.map((f) => {
            const d = deadlineDDay(f.prereg_end_at)
            return (
              <li key={f.id}>
                <Link to={`/fairs/${f.id}`} className="flex min-h-14 items-center gap-3 px-3 py-3 hover:bg-gray-50 sm:px-4">
                  <span className="font-display w-16 shrink-0 rounded-lg bg-red-50 py-1.5 text-center text-base tabular-nums text-red-600">
                    {/* 받아 둔 목록을 보는 사이 마감 시각이 지나면 d 가 null 이다 ('D-null' 로 보이던 문제) */}
                    {d == null ? '마감' : d === 0 ? '오늘' : `D-${d}`}
                  </span>
                  {/* 휴대폰은 제목 아래에 마감 시각 (한 줄에 두면 제목이 몇 글자만 보였다) */}
                  <span className="flex min-w-0 flex-1 flex-col sm:flex-row sm:items-center sm:gap-3">
                    <span className="line-clamp-2 break-words sm:flex-1 sm:truncate">{f.title}</span>
                    <span className="text-xs text-gray-500 sm:shrink-0">{formatDateTime(f.prereg_end_at)} 마감</span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Section>
  )
}

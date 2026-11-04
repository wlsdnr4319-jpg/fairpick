import { Link, useParams } from 'react-router-dom'
import { errorCode, errorMessage } from '../api/client'
import { StatusBadge, TagChip } from '../components/Badges'
import BookmarkButton from '../components/BookmarkButton'
import { MyVisit, Reviews, TagVotes } from '../components/FairEngagement'
import { ErrorState } from '../components/States'
import { useFair } from '../hooks/useFairs'
import { deadlineDDay, formatDateTime, formatPeriod, formatPrice, PUBLIC_ACCESS_LABEL } from '../utils/format'
import NotFound from './NotFound'

// 박람회 상세 (레퍼런스 4장 /fairs/:fairId, F-02)
export default function FairDetail() {
  const { fairId } = useParams()
  const { data: fair, isPending, isError, error, refetch } = useFair(fairId)

  if (isPending) return <p className="py-16 text-center text-gray-400">불러오는 중…</p>
  if (isError) {
    if (errorCode(error) === 'FAIR_NOT_FOUND' || errorCode(error) === 'VALIDATION_ERROR') return <NotFound />
    return <ErrorState message={errorMessage(error)} onRetry={refetch} />
  }

  const hours =
    fair.hours.open && fair.hours.close ? `${fair.hours.open.slice(0, 5)} ~ ${fair.hours.close.slice(0, 5)}` : '확인 중'

  return (
    <article className="space-y-8 pb-20 md:pb-0">
      <header className="space-y-3">
        <div className="flex items-center gap-2">
          <StatusBadge progress={fair.progress} dDay={fair.d_day} />
          <Link to={`/fairs?category=${fair.category.code}`} className="text-sm text-gray-500">
            {fair.category.name}
          </Link>
        </div>
        <h1 className="text-2xl font-bold">{fair.title}</h1>
        <div className="flex flex-wrap gap-1.5">
          {fair.tags.map((t) => (
            <TagChip key={t.slug} tag={t} asLink />
          ))}
        </div>
      </header>

      <section aria-label="핵심 정보" className="grid gap-3 rounded-xl border p-4 sm:grid-cols-2">
        <Info label="기간" value={formatPeriod(fair.start_date, fair.end_date)} />
        <Info label="운영 시간" value={hours} note={fair.hours.note} />
        <Info label="장소" value={`${fair.venue.name}${fair.venue.hall ? ` ${fair.venue.hall}` : ''} · ${fair.venue.region}`} />
        <Info label="일반인 관람" value={PUBLIC_ACCESS_LABEL[fair.public_access]} note={fair.access_note} />
        <Info label="현장 입장료" value={formatPrice(fair.price.onsite)} />
        <Info label="사전등록 입장료" value={formatPrice(fair.price.prereg)} />
      </section>

      <PreregBox prereg={fair.prereg} price={fair.price.prereg} />

      {(fair.summary || fair.visit_tip) && (
        <section className="space-y-4">
          {fair.summary && (
            <div>
              <h2 className="mb-1 font-semibold">소개</h2>
              {/* 관리자가 쓴 글도 React 기본 이스케이프로 출력한다 (dangerouslySetInnerHTML 금지) */}
              <p className="whitespace-pre-line text-gray-700">{fair.summary}</p>
            </div>
          )}
          {fair.visit_tip && (
            <div className="rounded-xl bg-amber-50 p-4">
              <h2 className="mb-1 font-semibold">관람 팁</h2>
              <p className="whitespace-pre-line text-gray-700">{fair.visit_tip}</p>
            </div>
          )}
        </section>
      )}

      <TagVotes fairId={fair.id} />
      <MyVisit fairId={fair.id} />
      <Reviews fairId={fair.id} />

      <footer className="space-y-1 text-sm text-gray-500">
        {fair.verified_at && <p>정보 확인일 {formatDateTime(fair.verified_at).split(' ')[0]}</p>}
        <p>일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.</p>
        <p>북마크 {fair.bookmark_count}명</p>
      </footer>

      {/* 모바일 하단 고정 바: 북마크, 공식 사이트 */}
      <div className="fixed inset-x-0 bottom-0 flex items-center gap-2 border-t bg-white px-4 py-2 md:static md:border-0 md:p-0">
        <BookmarkButton fairId={fair.id} bookmarked={fair.is_bookmarked} className="border shadow-none" />
        {fair.official_url && (
          <a
            href={fair.official_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 flex-1 items-center justify-center rounded-lg bg-indigo-600 px-4 text-white md:flex-none"
          >
            공식 사이트
          </a>
        )}
      </div>
    </article>
  )
}

function Info({ label, value, note }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium">{value}</p>
      {note && <p className="text-sm text-gray-600">{note}</p>}
    </div>
  )
}

function PreregBox({ prereg, price }) {
  if (!prereg.end_at && !prereg.url) return null
  const d = deadlineDDay(prereg.end_at)
  return (
    <section aria-label="사전등록" className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">사전등록</h2>
        {d != null && <span className="text-sm font-bold text-red-600">마감 {d === 0 ? '오늘' : `D-${d}`}</span>}
      </div>
      {prereg.end_at && (
        <p className="mt-1 text-sm text-gray-700">
          {prereg.start_at ? `${formatDateTime(prereg.start_at)} ~ ` : '~ '}
          {formatDateTime(prereg.end_at)}
        </p>
      )}
      {price === 0 && <p className="text-sm text-gray-700">사전등록하면 무료로 입장할 수 있어요</p>}
      {prereg.url && (
        <a
          href={prereg.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-4 text-white"
        >
          사전등록하러 가기
        </a>
      )}
    </section>
  )
}

import { Link } from 'react-router-dom'
import { formatDistance, formatPeriod } from '../utils/format'
import { StatusBadge, TagChip } from './Badges'
import BookmarkButton from './BookmarkButton'
import FairCover from './FairCover'

export default function FairCard({ fair }) {
  // 끝난 행사는 목록 맨 뒤에 오고(API 정렬), 표지를 흑백으로 그려 진행 중·예정과 구분한다.
  // 글자까지 흐리게 하면 대비가 모자라서(WCAG 4.5:1) 표지와 테두리만 바꾼다.
  // 휴대폰(sm 미만)은 왼쪽 작은 표지 + 오른쪽 글자의 가로 카드라 한 화면에 여러 개가 보인다. sm 부터는 위 표지 + 아래 글자.
  const ended = fair.progress === 'ended'
  return (
    // 카드 전체를 <a> 로 감싸면 북마크 <button> 이 링크 안에 들어가 HTML 규칙 위반이고 스크린리더가 헷갈린다.
    // 제목만 링크로 두고 ::after 로 카드 전체를 덮어 어디를 눌러도 이동하게 한다 (북마크는 그 위 z-10).
    <article
      data-ended={ended || undefined}
      className={`group relative flex overflow-hidden rounded-xl border bg-white transition-shadow hover:shadow-md focus-within:shadow-md sm:flex-col ${
        ended ? 'border-gray-100 bg-gray-50' : 'border-gray-200'
      }`}
    >
      <div className="relative min-h-32 w-32 shrink-0 bg-gray-100 sm:h-36 sm:min-h-0 sm:w-auto">
        {/* 공식 포스터는 저장하지 않는다. 올린 이미지 → 주제 예시 사진 → 일러스트 순서 (FairCover) */}
        <div className="absolute inset-0">
          <FairCover fair={fair} className={ended ? 'opacity-70 grayscale' : ''} />
        </div>
        <span className="absolute bottom-2 left-3 hidden rounded-full bg-white/90 px-2 py-0.5 text-xs font-semibold text-gray-800 sm:inline">
          {fair.category.name}
        </span>
        <div className="absolute top-2 left-2 sm:top-3 sm:left-3">
          <StatusBadge progress={fair.progress} dDay={fair.d_day} />
        </div>
      </div>
      <BookmarkButton fairId={fair.id} bookmarked={fair.is_bookmarked} className="absolute top-2 right-2 z-10" />
      <div className="min-w-0 flex-1 space-y-1 p-3 pr-12 sm:space-y-1.5 sm:p-4 sm:pr-4">
        <p className="text-xs text-gray-500 sm:hidden">{fair.category.name}</p>
        <h3 className="line-clamp-2 break-words font-semibold group-hover:text-indigo-700">
          <Link to={`/fairs/${fair.id}`} className="after:absolute after:inset-0 after:rounded-xl after:content-[''] focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:-outline-offset-2 focus-visible:after:outline-indigo-600">
            {fair.title}
          </Link>
        </h3>
        <p className="text-sm text-gray-600">{formatPeriod(fair.start_date, fair.end_date)}</p>
        <p className="truncate text-sm text-gray-600">
          {fair.venue.name}
          {fair.venue.hall ? ` ${fair.venue.hall}` : ''}
          {fair.distance_km != null && <span className="text-indigo-700"> · {formatDistance(fair.distance_km)}</span>}
        </p>
        {fair.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {fair.tags.map((t) => (
              <TagChip key={t.slug} tag={t} />
            ))}
          </div>
        )}
      </div>
    </article>
  )
}

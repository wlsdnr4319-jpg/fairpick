import { Link } from 'react-router-dom'
import { formatDistance, formatPeriod } from '../utils/format'
import { StatusBadge, TagChip } from './Badges'
import BookmarkButton from './BookmarkButton'
import FairCover from './FairCover'

export default function FairCard({ fair, compact = false }) {
  // 끝난 행사는 목록 맨 뒤에 오고(API 정렬), 표지를 흑백으로 그려 진행 중·예정과 구분한다.
  // 글자까지 흐리게 하면 대비가 모자라서(WCAG 4.5:1) 표지와 테두리만 바꾼다.
  const ended = fair.progress === 'ended'
  return (
    // 카드 전체를 <a> 로 감싸면 북마크 <button> 이 링크 안에 들어가 HTML 규칙 위반이고 스크린리더가 헷갈린다.
    // 제목만 링크로 두고 ::after 로 카드 전체를 덮어 어디를 눌러도 이동하게 한다 (북마크는 그 위 z-10).
    <article
      data-ended={ended || undefined}
      className={`group relative flex flex-col overflow-hidden rounded-xl border bg-white transition-shadow hover:shadow-md focus-within:shadow-md ${
        compact ? 'w-64 shrink-0' : ''
      } ${ended ? 'border-gray-100 bg-gray-50' : 'border-gray-200'}`}
    >
      <div className="relative h-36 bg-gray-100">
        {/* 공식 포스터는 저장하지 않고, 이미지가 없으면 제목·카테고리에 맞춘 일러스트를 그린다 */}
        <FairCover fair={fair} className={ended ? 'opacity-70 grayscale' : ''} />
        <span className="absolute bottom-2 left-3 rounded-full bg-white/90 px-2 py-0.5 text-xs font-semibold text-gray-800">
          {fair.category.name}
        </span>
        <div className="absolute left-3 top-3">
          <StatusBadge progress={fair.progress} dDay={fair.d_day} />
        </div>
        <BookmarkButton fairId={fair.id} bookmarked={fair.is_bookmarked} className="absolute right-2 top-2 z-10" />
      </div>
      <div className="min-w-0 space-y-1.5 p-4">
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

import { Link } from 'react-router-dom'
import { formatDistance, formatPeriod } from '../utils/format'
import { StatusBadge, TagChip } from './Badges'
import BookmarkButton from './BookmarkButton'
import FairCover from './FairCover'

export default function FairCard({ fair, compact = false }) {
  // 끝난 행사는 목록 맨 뒤에 오고(API 정렬), 카드도 흐리게 보여 진행 중·예정과 구분한다
  const ended = fair.progress === 'ended'
  return (
    <Link
      to={`/fairs/${fair.id}`}
      data-ended={ended || undefined}
      className={`group block overflow-hidden rounded-xl border border-gray-200 bg-white hover:shadow-md ${
        compact ? 'w-64 shrink-0' : ''
      } ${ended ? 'opacity-60 hover:opacity-100' : ''}`}
    >
      <div className="relative h-36 bg-gray-100">
        {/* 공식 포스터는 저장하지 않고, 이미지가 없으면 제목·카테고리에 맞춘 일러스트를 그린다 */}
        <FairCover fair={fair} className={ended ? 'grayscale' : ''} />
        <span className="absolute bottom-2 left-3 rounded-full bg-white/80 px-2 py-0.5 text-xs font-semibold text-gray-800">
          {fair.category.name}
        </span>
        <div className="absolute left-3 top-3">
          <StatusBadge progress={fair.progress} dDay={fair.d_day} />
        </div>
        <BookmarkButton fairId={fair.id} bookmarked={fair.is_bookmarked} className="absolute right-2 top-2" />
      </div>
      <div className="space-y-1.5 p-4">
        <h3 className="line-clamp-2 font-semibold group-hover:text-indigo-700">{fair.title}</h3>
        <p className="text-sm text-gray-600">{formatPeriod(fair.start_date, fair.end_date)}</p>
        <p className="text-sm text-gray-500">
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
    </Link>
  )
}

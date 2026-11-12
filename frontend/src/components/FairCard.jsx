import { Link } from 'react-router-dom'
import { formatDistance, formatPeriod } from '../utils/format'
import { StatusBadge, TagChip } from './Badges'
import BookmarkButton from './BookmarkButton'

// 이미지가 없으면 카테고리 기본 이미지 대신 카테고리 색 배경을 쓴다 (원문 이미지는 저장하지 않는다)
const CATEGORY_BG = {
  food: 'from-amber-200 to-orange-300',
  culture: 'from-pink-200 to-rose-300',
  lifestyle: 'from-teal-200 to-emerald-300',
  leisure: 'from-sky-200 to-blue-300',
  pet: 'from-yellow-200 to-lime-300',
  family: 'from-violet-200 to-purple-300',
  tech: 'from-slate-300 to-gray-400',
}

export default function FairCard({ fair, compact = false }) {
  return (
    <Link
      to={`/fairs/${fair.id}`}
      className={`group block overflow-hidden rounded-xl border border-gray-200 bg-white hover:shadow-md ${
        compact ? 'w-64 shrink-0' : ''
      }`}
    >
      <div className={`relative h-36 bg-gradient-to-br ${CATEGORY_BG[fair.category.code] ?? 'from-gray-200 to-gray-300'}`}>
        {fair.image_url && <img src={fair.image_url} alt="" className="h-full w-full object-cover" />}
        {!fair.image_url && (
          <span className="absolute bottom-2 left-3 text-sm font-semibold text-white/90">{fair.category.name}</span>
        )}
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

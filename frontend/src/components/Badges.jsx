import { Link } from 'react-router-dom'
import { statusLabel } from '../utils/format'

const STATUS_STYLE = {
  ongoing: 'bg-green-600 text-white',
  upcoming: 'bg-indigo-600 text-white',
  ended: 'bg-gray-400 text-white',
}

export function StatusBadge({ progress, dDay }) {
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[progress]}`}>
      {statusLabel(progress, dDay)}
    </span>
  )
}

export function TagChip({ tag, selected = false, onClick, asLink = false }) {
  const style = `inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs ${
    selected ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-gray-300 text-gray-600'
  }`
  if (asLink) {
    return (
      <Link to={`/fairs?tags=${tag.slug}`} className={style}>
        #{tag.name}
      </Link>
    )
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} aria-pressed={selected} className={`${style} min-h-9 px-3`}>
        #{tag.name}
      </button>
    )
  }
  return <span className={style}>#{tag.name}</span>
}

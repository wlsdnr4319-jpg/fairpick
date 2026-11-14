import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useCategories, useTags, useVenues } from '../hooks/useFairs'
import { useMyLocation } from '../hooks/useMyLocation'
import { TagChip } from './Badges'

// 필터 상태는 URL 쿼리스트링에 저장한다. 예: /fairs?category=food&tags=date&free=true (레퍼런스 4장)
const PERIODS = [
  ['', '전체 기간'],
  ['this_weekend', '이번 주말'],
  ['this_month', '이번 달'],
  ['ongoing', '진행 중'],
  ['upcoming', '예정'],
]
const SORTS = [
  ['start_date', '개막순'],
  ['prereg_deadline', '사전등록 마감 임박순'],
  ['popular', '인기순'],
]
const DISTANCE_SORT = ['distance', '가까운 순'] // 위치가 있을 때만 고를 수 있다
const RADII = [
  ['', '거리 제한 없음'],
  ['10', '10km 이내'],
  ['30', '30km 이내'],
  ['100', '100km 이내'],
]

export default function FilterBar() {
  const [params, setParams] = useSearchParams()
  const { data: categories = [] } = useCategories()
  const { data: tags = [] } = useTags()
  const { data: venues = [] } = useVenues()
  const regions = [...new Set(venues.map((v) => v.region))]

  const selectedTags = (params.get('tags') ?? '').split(',').filter(Boolean)

  // 필터를 바꾸면 1페이지로 돌아간다
  const update = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    next.delete('page')
    setParams(next)
  }

  const toggleTag = (slug) => {
    const set = new Set(selectedTags)
    if (set.has(slug)) set.delete(slug)
    else set.add(slug)
    update({ tags: [...set].join(',') })
  }

  const hasLocation = params.has('lat') && params.has('lng')
  const sorts = hasLocation ? [...SORTS, DISTANCE_SORT] : SORTS

  const select = 'min-h-11 rounded-lg border border-gray-300 bg-white px-3 text-sm'
  const check = 'flex min-h-11 items-center gap-2 text-sm'

  return (
    <section aria-label="필터" className="space-y-3 rounded-xl bg-gray-50 p-4">
      {/* URL 의 검색어가 바뀌면(뒤로 가기 등) key 가 바뀌어 입력창을 새로 그린다 */}
      <SearchBox key={params.get('q') ?? ''} initial={params.get('q') ?? ''} onSearch={(q) => update({ q })} />

      <div className="flex flex-wrap gap-2">
        <select aria-label="카테고리" className={select} value={params.get('category') ?? ''} onChange={(e) => update({ category: e.target.value })}>
          <option value="">전체 카테고리</option>
          {categories.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
        <select aria-label="지역" className={select} value={params.get('region') ?? ''} onChange={(e) => update({ region: e.target.value })}>
          <option value="">전체 지역</option>
          {regions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <select aria-label="기간" className={select} value={params.get('period') ?? ''} onChange={(e) => update({ period: e.target.value })}>
          {PERIODS.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
        <select aria-label="정렬" className={select} value={params.get('sort') ?? 'start_date'} onChange={(e) => update({ sort: e.target.value === 'start_date' ? '' : e.target.value })}>
          {sorts.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
        <label className={check}>
          <input type="checkbox" checked={params.get('free') === 'true'} onChange={(e) => update({ free: e.target.checked ? 'true' : '' })} />
          무료만
        </label>
        <label className={check}>
          <input type="checkbox" checked={params.get('public_only') === 'true'} onChange={(e) => update({ public_only: e.target.checked ? 'true' : '' })} />
          일반인 관람 가능만
        </label>
      </div>

      <NearbyControl
        hasLocation={hasLocation}
        radius={params.get('radius_km') ?? ''}
        onLocate={({ lat, lng }) => update({ lat: String(lat), lng: String(lng), sort: 'distance' })}
        onRadius={(radius_km) => update({ radius_km })}
        onClear={() => update({ lat: '', lng: '', radius_km: '', sort: params.get('sort') === 'distance' ? '' : params.get('sort') })}
        selectClass={select}
      />

      <div className="flex flex-wrap gap-1.5" aria-label="태그">
        {tags.map((t) => (
          <TagChip key={t.slug} tag={t} selected={selectedTags.includes(t.slug)} onClick={() => toggleTag(t.slug)} />
        ))}
      </div>
    </section>
  )
}

// 내 주변 박람회: 버튼을 눌렀을 때만 위치를 묻는다 (페이지를 열자마자 권한 창을 띄우지 않는다)
function NearbyControl({ hasLocation, radius, onLocate, onRadius, onClear, selectClass }) {
  const state = useMyLocation()

  const locate = async () => {
    const found = await state.locate()
    if (found) onLocate(found)
  }

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={locate}
          disabled={state.loading}
          className="min-h-11 rounded-lg border border-indigo-300 bg-white px-4 text-sm text-indigo-700 disabled:opacity-60"
        >
          {state.loading ? '위치 확인 중…' : hasLocation ? '내 위치 다시 찾기' : '내 주변 박람회'}
        </button>
        {hasLocation && (
          <>
            <select aria-label="거리" className={selectClass} value={radius} onChange={(e) => onRadius(e.target.value)}>
              {RADII.map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
            <button type="button" onClick={onClear} className="min-h-11 px-2 text-sm text-gray-500 underline">
              위치 지우기
            </button>
          </>
        )}
      </div>
      {state.error && (
        <p role="alert" className="text-sm text-red-600">
          {state.error}
        </p>
      )}
      {hasLocation && !state.error && <p className="text-xs text-gray-500">위치는 약 1km 단위로만 쓰고 저장하지 않아요.</p>}
    </div>
  )
}

function SearchBox({ initial, onSearch }) {
  const [q, setQ] = useState(initial)
  return (
    <form
      role="search"
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch(q.trim())
      }}
    >
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="예: 커피, 캠핑, 일러스트…"
        aria-label="검색어"
        className="min-h-11 min-w-0 flex-1 rounded-lg border border-gray-300 px-3"
      />
      <button type="submit" className="min-h-11 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-4 text-white">
        검색
      </button>
    </form>
  )
}

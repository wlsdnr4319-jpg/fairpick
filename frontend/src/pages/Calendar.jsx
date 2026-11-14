import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchCalendar } from '../api/engagement'
import { paletteFor } from '../utils/cover'
import { formatPeriod, shortTitle } from '../utils/format'

// 월간 캘린더 (F-17). 월과 고른 날은 URL 의 ?month=2026-11&day=14 로 기억한다 (공유·새로고침해도 그대로).
// 칸에는 그날의 큰 행사(규모 점수 scale 순) 2개만 짧게, 날짜를 누르면 오른쪽(좁은 화면은 아래) 상자에 그날 행사 전체.
// 휴대폰은 칸이 좁아 이름 대신 개수만 보여 준다.

const WEEK = ['일', '월', '화', '수', '목', '금', '토']
const PER_CELL = 2

const pad = (n) => String(n).padStart(2, '0')

function shift(month, delta) {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

const bigFirst = (a, b) => b.scale - a.scale || a.start_date.localeCompare(b.start_date) || a.id - b.id

export default function Calendar() {
  const [params, setParams] = useSearchParams()
  const [now] = useState(() => new Date()) // 첫 렌더 때 한 번만 읽는다
  const thisMonth = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  const month = params.get('month') ?? thisMonth
  const { data: fairs = [], isPending } = useQuery({ queryKey: ['calendar', month], queryFn: () => fetchCalendar(month) })

  const [y, m] = month.split('-').map(Number)
  const firstDow = new Date(y, m - 1, 1).getDay()
  const days = new Date(y, m, 0).getDate()
  const cells = [...Array(firstDow).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)]
  const todayKey = `${thisMonth}-${pad(now.getDate())}`

  const on = (day) => {
    const key = `${month}-${pad(day)}`
    return fairs.filter((f) => f.start_date <= key && f.end_date >= key).sort(bigFirst)
  }

  // 고른 날: 주소의 day → 이번 달이면 오늘 → 행사가 있는 첫날 → 1일
  const asked = Number(params.get('day'))
  const firstBusy = Array.from({ length: days }, (_, i) => i + 1).find((d) => on(d).length > 0)
  const selected = asked >= 1 && asked <= days ? asked : month === thisMonth ? now.getDate() : (firstBusy ?? 1)
  const dayList = on(selected)
  const dow = WEEK[new Date(y, m - 1, selected).getDay()]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">
          {y}년 {m}월
        </h1>
        <div className="flex gap-2">
          {month !== thisMonth && (
            <button type="button" className="min-h-11 rounded-lg border px-3 text-sm" onClick={() => setParams({})}>
              오늘
            </button>
          )}
          <button type="button" className="min-h-11 rounded-lg border px-3" onClick={() => setParams({ month: shift(month, -1) })} aria-label="이전 달">
            ‹
          </button>
          <button type="button" className="min-h-11 rounded-lg border px-3" onClick={() => setParams({ month: shift(month, 1) })} aria-label="다음 달">
            ›
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_18rem] xl:items-start">
        <div className="space-y-2">
          {isPending && <p className="text-gray-400">불러오는 중…</p>}
          <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border bg-gray-200 text-xs">
            {WEEK.map((w, i) => (
              <div key={w} className={`bg-gray-50 py-2 text-center font-semibold ${i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : ''}`}>
                {w}
              </div>
            ))}
            {cells.map((day, i) => {
              if (!day) return <div key={`empty-${i}`} className="bg-gray-50" />
              const key = `${month}-${pad(day)}`
              const list = on(day)
              const picked = day === selected
              const col = i % 7
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setParams({ month, day: String(day) })}
                  aria-pressed={picked}
                  aria-label={`${m}월 ${day}일, 박람회 ${list.length}개`}
                  className={`flex min-h-14 flex-col items-center gap-1 p-1 text-left sm:min-h-24 sm:items-stretch ${
                    picked ? 'bg-indigo-50 ring-2 ring-inset ring-indigo-500' : 'bg-white hover:bg-gray-50'
                  } ${key === todayKey && !picked ? 'ring-1 ring-inset ring-indigo-300' : ''}`}
                >
                  <span
                    className={`text-center sm:text-left ${key === todayKey ? 'font-bold text-indigo-700' : col === 0 ? 'text-red-500' : col === 6 ? 'text-blue-500' : 'text-gray-600'}`}
                  >
                    {day}
                  </span>
                  {/* 휴대폰: 개수만 */}
                  {list.length > 0 && (
                    <span className="min-w-5 rounded-full bg-indigo-100 px-1 text-center text-[11px] font-semibold text-indigo-700 sm:hidden">
                      {list.length}
                    </span>
                  )}
                  {/* 넓은 화면: 큰 행사 2개 + 나머지 개수 */}
                  <span className="hidden space-y-0.5 sm:block">
                    {list.slice(0, PER_CELL).map((f) => {
                      const c = paletteFor(f.category)
                      return (
                        <span
                          key={f.id}
                          data-fair={f.id}
                          className="block truncate rounded px-1 py-px text-[11px] leading-4 font-medium"
                          style={{ background: c.from, color: c.ink }}
                        >
                          {shortTitle(f.title)}
                        </span>
                      )
                    })}
                    {list.length > PER_CELL && <span className="block px-1 text-[11px] text-gray-500">+{list.length - PER_CELL}</span>}
                  </span>
                </button>
              )
            })}
          </div>
          <p className="hidden text-xs text-gray-500 sm:block">
            칸에는 규모가 큰 행사 {PER_CELL}개까지 보여요 (관심 북마크·전시홀·기간 기준). 날짜를 누르면 그날 행사를 모두 볼 수 있어요.
          </p>
          <p className="text-xs text-gray-500 sm:hidden">숫자는 그날 열리는 박람회 수예요. 날짜를 누르면 아래에 목록이 나와요.</p>
        </div>

        <section aria-labelledby="day-list-title" aria-live="polite" className="rounded-xl border bg-white p-4 xl:sticky xl:top-6">
          <h2 id="day-list-title" className="font-semibold">
            {m}월 {selected}일 ({dow}) <span className="text-gray-500">· 박람회 {dayList.length}개</span>
          </h2>
          {dayList.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">이 날 열리는 박람회가 없어요</p>
          ) : (
            <ul className="mt-3 divide-y xl:max-h-[70vh] xl:overflow-y-auto xl:overscroll-contain">
              {dayList.map((f) => {
                const c = paletteFor(f.category)
                return (
                  <li key={f.id}>
                    <Link to={`/fairs/${f.id}`} className="group block space-y-0.5 py-3 first:pt-0">
                      <span className="flex items-center gap-1.5 text-xs text-gray-500">
                        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: c.accent }} aria-hidden="true" />
                        {f.category_name}
                        {f.bookmark_count > 0 && <span>· 북마크 {f.bookmark_count}</span>}
                      </span>
                      <span className="block font-medium break-words group-hover:text-indigo-700 group-hover:underline">{f.title}</span>
                      <span className="block text-sm text-gray-600">{formatPeriod(f.start_date, f.end_date)}</span>
                      <span className="block text-sm text-gray-600">
                        {f.venue}
                        {f.hall ? ` ${f.hall}` : ''} · {f.region}
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}

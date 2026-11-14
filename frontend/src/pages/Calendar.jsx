import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchCalendar } from '../api/engagement'
import { useIsPhone } from '../hooks/useMediaQuery'

// 월간 캘린더에 박람회 기간 표시 (F-17). 월은 URL 의 ?month=2026-11 로 기억한다
const WEEK = ['일', '월', '화', '수', '목', '금', '토']
const pad = (n) => String(n).padStart(2, '0')

function shift(month, delta) {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

export default function Calendar() {
  const [params, setParams] = useSearchParams()
  const [now] = useState(() => new Date()) // 첫 렌더 때 한 번만 읽는다
  const month = params.get('month') ?? `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  const { data: fairs = [], isPending } = useQuery({ queryKey: ['calendar', month], queryFn: () => fetchCalendar(month) })

  const [y, m] = month.split('-').map(Number)
  const firstDow = new Date(y, m - 1, 1).getDay()
  const days = new Date(y, m, 0).getDate()
  const cells = [...Array(firstDow).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)]
  const todayKey = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`

  // 휴대폰에서 고른 날. 다른 달로 넘어가면 이번 달이면 오늘, 아니면 1일
  const phone = useIsPhone()
  const [picked, setPicked] = useState(null)
  const isThisMonth = month === `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  const selected = picked?.month === month ? picked.day : isThisMonth ? now.getDate() : 1

  const on = (day) => {
    const key = `${month}-${pad(day)}`
    return fairs.filter((f) => f.start_date <= key && f.end_date >= key)
  }

  const dayList = phone ? on(selected) : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{y}년 {m}월</h1>
        <div className="flex gap-2">
          <button type="button" className="min-h-11 rounded-lg border px-3" onClick={() => setParams({ month: shift(month, -1) })} aria-label="이전 달">‹</button>
          <button type="button" className="min-h-11 rounded-lg border px-3" onClick={() => setParams({ month: shift(month, 1) })} aria-label="다음 달">›</button>
        </div>
      </div>
      {isPending && <p className="text-gray-400">불러오는 중…</p>}
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border bg-gray-200 text-xs">
        {WEEK.map((w, i) => (
          <div key={w} className={`bg-gray-50 py-2 text-center font-semibold ${i === 0 ? 'text-red-500' : i === 6 ? 'text-blue-500' : ''}`}>
            {w}
          </div>
        ))}
        {cells.map((day, i) => {
          const list = day ? on(day) : []
          const key = day ? `${month}-${pad(day)}` : `empty-${i}`
          const today = key === todayKey
          if (phone) {
            // 휴대폰: 칸이 좁아 제목이 '202…' 처럼 잘렸다. 칸에는 날짜와 개수만, 누르면 아래에 그날 목록
            if (!day) return <div key={key} className="bg-white" />
            const picked = day === selected
            return (
              <button
                key={key}
                type="button"
                onClick={() => setPicked({ month, day })}
                aria-pressed={picked}
                aria-label={`${m}월 ${day}일, 박람회 ${list.length}개`}
                className={`flex min-h-14 flex-col items-center gap-1 py-1.5 ${picked ? 'bg-indigo-600 text-white' : 'bg-white'} ${
                  today && !picked ? 'ring-2 ring-inset ring-indigo-400' : ''
                }`}
              >
                <span className={picked ? 'font-semibold' : 'text-gray-600'}>{day}</span>
                {list.length > 0 && (
                  <span className={`min-w-5 rounded-full px-1 text-[11px] font-semibold ${picked ? 'bg-white text-indigo-700' : 'bg-indigo-50 text-indigo-700'}`}>
                    {list.length}
                  </span>
                )}
              </button>
            )
          }
          return (
            <div key={key} className={`min-h-24 bg-white p-1 ${today ? 'ring-2 ring-inset ring-indigo-400' : ''}`}>
              {day && <p className="mb-1 text-gray-500">{day}</p>}
              {list.slice(0, 3).map((f) => (
                <Link key={f.id} to={`/fairs/${f.id}`} title={`${f.title} · ${f.venue}`} className="mb-0.5 block truncate rounded bg-indigo-50 px-1 text-indigo-800">
                  {f.title}
                </Link>
              ))}
              {list.length > 3 && <p className="text-gray-400">+{list.length - 3}</p>}
            </div>
          )
        })}
      </div>

      {phone && (
        <section aria-labelledby="day-list-title" className="space-y-2">
          <h2 id="day-list-title" className="font-semibold">
            {m}월 {selected}일 박람회 {dayList.length}개
          </h2>
          {dayList.length === 0 ? (
            <p className="text-sm text-gray-500">이 날 열리는 박람회가 없어요</p>
          ) : (
            <ul className="divide-y rounded-xl border">
              {dayList.map((f) => (
                <li key={f.id}>
                  <Link to={`/fairs/${f.id}`} className="block min-h-12 px-4 py-3 hover:bg-gray-50">
                    <span className="block break-words font-medium">{f.title}</span>
                    <span className="text-sm text-gray-500">{f.venue}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}

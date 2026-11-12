import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'

// 통계 리포트 (레퍼런스 12장, F-19): 언제, 어디서, 어떤 박람회가 많이 열리는가.
// 카테고리 색은 순위가 아니라 카테고리(엔티티)에 고정한다. 7색은 색각 이상 검사(validate_palette.js)를 통과했고,
// 흰 배경 대비가 3:1 미만인 색이 있어 범례와 표 보기를 함께 둔다.
const CATEGORY_COLOR = {
  food: '#2a78d6',
  culture: '#eb6834',
  lifestyle: '#1baf7a',
  leisure: '#eda100',
  pet: '#e87ba4',
  family: '#008300',
  tech: '#6250d6',
}
const INK = { muted: '#898781', grid: '#e1e0d9', axis: '#c3c2b7' }
const SINGLE = '#2a78d6'
// 전시장 색: 같은 검증 팔레트에서 전시장마다 고정 (전시장이 늘어도 기존 색이 바뀌지 않게 이름으로 정한다)
const VENUE_COLOR = {
  코엑스: '#2a78d6',
  SETEC: '#eb6834',
  킨텍스: '#1baf7a',
  엑스코: '#eda100',
  '코엑스 마곡': '#e87ba4',
  수원메쎄: '#6250d6',
}
const VENUE_FALLBACK = ['#008300', '#898781']
const venueColor = (name, i) => VENUE_COLOR[name] ?? VENUE_FALLBACK[i % VENUE_FALLBACK.length]
// 히트맵: 파랑 한 가지 계열, 연한 색 = 적음 (팔레트 sequential 100~700)
const HEAT = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']

const get = (url, params) => api.get(url, { params }).then((r) => r.data)

export default function Report() {
  const [year, setYear] = useState(2026)
  const overview = useQuery({ queryKey: ['stats', 'overview'], queryFn: () => get('/stats/overview') })
  const monthly = useQuery({ queryKey: ['stats', 'monthly', year], queryFn: () => get('/stats/monthly', { year }) })
  const categories = useQuery({ queryKey: ['stats', 'categories'], queryFn: () => get('/stats/categories') })
  const venues = useQuery({ queryKey: ['stats', 'venues'], queryFn: () => get('/stats/venues') })
  const history = useQuery({ queryKey: ['stats', 'history'], queryFn: () => get('/stats/history') })

  return (
    <div className="space-y-10">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">박람회 통계</h1>
        <p className="text-sm text-gray-500">페어픽에 모인 박람회 기준. 지난 행사도 포함하고 검수 전 초안은 뺐어요.</p>
      </header>

      {overview.data && (
        <section aria-label="요약" className="grid grid-cols-3 gap-3">
          <Kpi label="박람회" value={`${overview.data.total}개`} />
          <Kpi label="무료로 갈 수 있는 비율" value={`${Math.round(overview.data.free_ratio * 100)}%`} note="현장 또는 사전등록 무료" />
          <Kpi label="평균 개최 기간" value={`${overview.data.avg_days}일`} />
        </section>
      )}

      <MonthlySection year={year} setYear={setYear} rows={monthly.data} categories={categories.data ?? []} />
      <CategorySection rows={categories.data} />
      <VenueSection rows={venues.data} />
      <HistorySection data={history.data} />
    </div>
  )
}

function Kpi({ label, value, note }) {
  return (
    <div className="rounded-xl border p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {note && <p className="text-xs text-gray-400">{note}</p>}
    </div>
  )
}

function Section({ title, lead, action, children }) {
  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {lead && <p className="text-sm text-gray-600">{lead}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

const axisProps = { tick: { fill: INK.muted, fontSize: 12 }, axisLine: { stroke: INK.axis }, tickLine: false }

function MonthlySection({ year, setYear, rows, categories }) {
  const [asTable, setAsTable] = useState(false)
  if (!rows) return null
  const data = rows.map((r) => ({ month: `${Number(r.month.slice(5))}월`, total: r.total, ...r.by_category }))
  const used = categories.filter((c) => rows.some((r) => r.by_category[c.code]))
  const peak = rows.reduce((a, b) => (b.total > a.total ? b : a), rows[0])

  return (
    <Section
      title={`${year}년 월별 개최 수`}
      lead={peak.total ? `${Number(peak.month.slice(5))}월에 가장 많이 열렸어요 (${peak.total}개)` : '이 해의 데이터가 없어요'}
      action={
        <div className="flex gap-2 text-sm">
          <select aria-label="연도" className="min-h-11 rounded-lg border px-2" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {[2025, 2026, 2027].map((y) => <option key={y} value={y}>{y}년</option>)}
          </select>
          <button type="button" className="min-h-11 rounded-lg border px-3" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
            {asTable ? '차트로 보기' : '표로 보기'}
          </button>
        </div>
      }
    >
      {asTable ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-right text-sm">
            <thead className="border-b text-gray-500">
              <tr>
                <th className="py-2 text-left">월</th>
                {used.map((c) => <th key={c.code}>{c.name}</th>)}
                <th>합계</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.month} className="border-b">
                  <td className="py-1.5 text-left">{r.month}</td>
                  {used.map((c) => <td key={c.code}>{r[c.code] ?? 0}</td>)}
                  <td className="font-semibold">{r.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={INK.grid} />
              <XAxis dataKey="month" {...axisProps} />
              <YAxis allowDecimals={false} {...axisProps} axisLine={false} />
              <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} formatter={(v, name) => [`${v}개`, name]} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12, color: '#52514e' }} />
              {used.map((c) => (
                // 쌓인 막대 사이 2px 흰 간격으로 구분한다
                <Bar key={c.code} dataKey={c.code} name={c.name} stackId="m" fill={CATEGORY_COLOR[c.code]} stroke="#fff" strokeWidth={2} maxBarSize={36} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Section>
  )
}

function HBar({ data, dataKey, nameKey, height }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 32, left: 8, bottom: 0 }}>
          <XAxis type="number" hide allowDecimals={false} />
          <YAxis type="category" dataKey={nameKey} width={92} {...axisProps} />
          <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} formatter={(v) => [`${v}개`, '박람회']} />
          <Bar dataKey={dataKey} fill={SINGLE} radius={[0, 4, 4, 0]} barSize={16}>
            <LabelList dataKey={dataKey} position="right" fill="#52514e" fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function CategorySection({ rows }) {
  if (!rows) return null
  const top = rows[0]
  return (
    <Section title="카테고리별 개최 수" lead={top?.count ? `${top.name} 박람회가 가장 많아요` : null}>
      <HBar data={rows} dataKey="count" nameKey="name" height={rows.length * 36} />
      <div className="overflow-x-auto">
        <table className="w-full text-right text-sm">
          <thead className="border-b text-gray-500">
            <tr>
              <th className="py-2 text-left">카테고리</th>
              <th>개최 수</th>
              <th>평균 기간</th>
              <th>무료 비율</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.code} className="border-b">
                <td className="py-1.5 text-left">{r.name}</td>
                <td>{r.count}</td>
                <td>{r.count ? `${r.avg_days}일` : '-'}</td>
                <td>{r.count ? `${Math.round(r.free_ratio * 100)}%` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  )
}

function VenueSection({ rows }) {
  if (!rows || rows.length === 0) return null
  return (
    <Section title="전시장별 개최 수" lead={`${rows[0].venue}에서 가장 많이 열려요. 가장 많은 카테고리: ${rows[0].top_category}`}>
      <HBar data={rows} dataKey="count" nameKey="venue" height={rows.length * 36} />
    </Section>
  )
}

// 받침이 있으면 '은', 없으면 '는' (웨딩은, 식음료는)
function topicParticle(word) {
  const code = word.charCodeAt(word.length - 1) - 0xac00
  return code >= 0 && code < 11172 && code % 28 !== 0 ? '은' : '는'
}

// 지난 행사 기록 (fair_archive): 연도별 흐름과 주제별로 많이 열리는 달
function HistorySection({ data }) {
  if (!data || data.total === 0) return null
  return (
    <div className="space-y-10 border-t pt-8">
      <header className="space-y-1">
        <h2 className="text-xl font-bold">
          지난 {data.to_year - data.from_year + 1}년의 박람회 ({data.from_year}~{data.to_year})
        </h2>
        <p className="text-sm text-gray-500">
          {data.venues.join('·')} 공식 일정 {data.total.toLocaleString()}건을 모았어요. 개막일 기준이고, 학회·회의는 뺐어요.
        </p>
      </header>
      <YearlySection data={data} />
      <ThemeMonthSection data={data} />
    </div>
  )
}

function YearlySection({ data }) {
  const [asTable, setAsTable] = useState(false)
  const rows = data.by_year.map((y) => ({ year: `${y.year}`, total: y.total, ...y.by_venue }))
  // 해마다 비교는 첫해부터 기록이 있는 전시장끼리만 한다. 중간에 기록이 시작된 곳을 더하면 늘어난 것처럼 보인다
  const since = data.venue_since ?? {}
  const late = data.venues.filter((v) => (since[v] ?? data.from_year) > data.from_year)
  const steady = data.venues.filter((v) => !late.includes(v))
  const counted = data.by_year
    .map((y) => ({ year: y.year, total: steady.reduce((sum, v) => sum + (y.by_venue[v] ?? 0), 0) }))
    .filter((y) => y.total > 0)
  const low = counted.reduce((a, b) => (b.total < a.total ? b : a), counted[0])
  const high = counted.reduce((a, b) => (b.total > a.total ? b : a), counted[0])
  const basis = late.length ? `${steady.length}곳 기준 ` : ''
  return (
    <Section
      title="연도별 개최 수"
      lead={`${basis}가장 적은 해는 ${low.year}년(${low.total}개), 가장 많은 해는 ${high.year}년(${high.total}개)이에요`}
      action={
        <button type="button" className="min-h-11 rounded-lg border px-3 text-sm" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
          {asTable ? '차트로 보기' : '표로 보기'}
        </button>
      }
    >
      {asTable ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-right text-sm">
            <thead className="border-b text-gray-500">
              <tr>
                <th className="py-2 text-left">연도</th>
                {data.venues.map((v) => <th key={v}>{v}</th>)}
                <th>합계</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.year} className="border-b">
                  <td className="py-1.5 text-left">{r.year}</td>
                  {data.venues.map((v) => <td key={v}>{r[v]}</td>)}
                  <td className="font-semibold">{r.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={INK.grid} />
              <XAxis dataKey="year" {...axisProps} />
              <YAxis allowDecimals={false} {...axisProps} axisLine={false} />
              <Tooltip cursor={{ fill: 'rgba(0,0,0,0.04)' }} formatter={(v, name) => [`${v}개`, name]} />
              <Legend iconType="square" wrapperStyle={{ fontSize: 12, color: '#52514e' }} />
              {data.venues.map((v, i) => (
                <Bar key={v} dataKey={v} name={v} stackId="y" fill={venueColor(v, i)} stroke="#fff" strokeWidth={2} maxBarSize={44} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {late.length > 0 && (
        <p className="text-xs text-gray-500">
          {late.map((v) => `${v}${topicParticle(v)} ${since[v]}년`).join(', ')}부터 공식 일정 기록이 있어요. 그 전 해는 0건이 아니라 기록이 없는 거예요.
        </p>
      )}
    </Section>
  )
}

// 주제 표에서 뺀 것: 박람회가 아닌 행사(입주박람회, 선거 개표·공연 등)와 주제를 못 찾은 행사
function excludedNote(data) {
  const parts = Object.entries(data.excluded ?? {})
    .filter(([, n]) => n > 0)
    .map(([name, n]) => `${name} ${n.toLocaleString()}건`)
  if (data.other_total > 0) parts.push(`주제를 못 찾은 ${data.other_total.toLocaleString()}건`)
  return parts.length ? `제목 키워드로 나눴고, ${parts.join(' · ')}은 뺐어요` : '제목 키워드로 나눴어요'
}

function ThemeMonthSection({ data }) {
  const themes = data.themes.filter((t) => t.total > 0)
  const max = Math.max(1, ...themes.flatMap((t) => t.by_month))
  const years = data.to_year - data.from_year + 1
  const busiest = [...themes].sort((a, b) => b.total - a.total).slice(0, 3)
  const months = (list) => list.map((m) => `${m}월`).join('·')
  return (
    <Section
      title="주제별로 많이 열리는 달"
      lead={busiest.map((t) => `${t.theme}${topicParticle(t.theme)} ${months(t.peak_months)}`).join(', ') + '에 가장 많이 열렸어요'}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-separate border-spacing-0.5 text-center text-xs">
          <caption className="sr-only">주제와 달별 개최 수 ({years}년 합계, 개막일 기준)</caption>
          <thead className="text-gray-500">
            <tr>
              <th className="py-1 text-left font-normal">주제</th>
              {Array.from({ length: 12 }, (_, i) => <th key={i} className="font-normal">{i + 1}월</th>)}
              <th className="pl-2 text-right font-normal">합계</th>
            </tr>
          </thead>
          <tbody>
            {themes.map((t) => (
              <tr key={t.theme}>
                <th scope="row" className="whitespace-nowrap py-1 pr-2 text-left font-medium text-gray-700">{t.theme}</th>
                {t.by_month.map((n, i) => {
                  const step = n === 0 ? -1 : Math.min(HEAT.length - 1, Math.floor((n / max) * HEAT.length))
                  return (
                    <td
                      key={i}
                      title={`${t.theme} · ${i + 1}월: ${n}개 (${years}년 합계)`}
                      className="h-9 rounded"
                      style={{
                        background: step < 0 ? '#f5f5f3' : HEAT[step],
                        color: step >= 4 ? '#fff' : step < 0 ? '#b5b4ad' : '#1f1f1d',
                      }}
                    >
                      {n || '·'}
                    </td>
                  )
                })}
                <td className="pl-2 text-right font-semibold text-gray-700">{t.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-2 text-xs text-gray-500" aria-hidden="true">
        <span>적음</span>
        {HEAT.map((c) => <span key={c} className="h-3 w-6 rounded-sm" style={{ background: c }} />)}
        <span>많음</span>
        <span className="ml-auto">{excludedNote(data)}</span>
      </div>
    </Section>
  )
}

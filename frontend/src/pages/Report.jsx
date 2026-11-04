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

const get = (url, params) => api.get(url, { params }).then((r) => r.data)

export default function Report() {
  const [year, setYear] = useState(2026)
  const overview = useQuery({ queryKey: ['stats', 'overview'], queryFn: () => get('/stats/overview') })
  const monthly = useQuery({ queryKey: ['stats', 'monthly', year], queryFn: () => get('/stats/monthly', { year }) })
  const categories = useQuery({ queryKey: ['stats', 'categories'], queryFn: () => get('/stats/categories') })
  const venues = useQuery({ queryKey: ['stats', 'venues'], queryFn: () => get('/stats/venues') })

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

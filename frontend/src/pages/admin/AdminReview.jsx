import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useCategories, useTags, useVenues } from '../../hooks/useFairs'

// 수집 검수 (레퍼런스 4장 /admin/review, F-10)
// 수집된 항목마다 원본 텍스트와 정규화 결과를 나란히 보여주고, 관리자가 일반인 관람 여부·입장료·태그·관람 팁을 채운 뒤 승인한다.
export default function AdminReview() {
  const qc = useQueryClient()
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['admin', 'review'],
    queryFn: () => api.get('/admin/crawled-items', { params: { review_status: 'pending', size: 50 } }).then((r) => r.data),
  })
  const done = () => qc.invalidateQueries({ queryKey: ['admin'] })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">수집 검수 {data ? `(${data.total})` : ''}</h1>
        <div className="flex gap-3 text-sm">
          <Sources onRun={done} />
          <Link to="/admin/crawl-runs" className="underline">
            수집 이력
          </Link>
        </div>
      </div>
      {isPending && <p className="text-gray-400">불러오는 중…</p>}
      {isError && <button onClick={() => refetch()}>다시 시도</button>}
      {data && data.items.length === 0 && <p className="rounded-xl border border-dashed p-8 text-center text-gray-500">검수할 항목이 없어요</p>}
      <ul className="space-y-4">
        {data?.items.map((item) => (
          <ReviewItem key={item.id} item={item} onDone={done} />
        ))}
      </ul>
    </div>
  )
}

function Sources({ onRun }) {
  const { data: sources = [] } = useQuery({ queryKey: ['admin', 'sources'], queryFn: () => api.get('/admin/crawl-sources').then((r) => r.data) })
  const [msg, setMsg] = useState('')
  const run = useMutation({
    mutationFn: (id) => api.post(`/admin/crawl-sources/${id}/run`).then((r) => r.data),
    onSuccess: (r) => {
      setMsg(r.status === 'succeeded' ? `${r.source}: 신규 ${r.new_count}, 변경 ${r.changed_count}` : `${r.source}: 실패`)
      onRun()
    },
    onError: (e) => setMsg(errorMessage(e)),
  })
  return (
    <span className="flex items-center gap-2">
      {sources.map((s) => (
        <button key={s.id} type="button" disabled={run.isPending} onClick={() => run.mutate(s.id)} className="rounded border px-2 py-1">
          {s.venue} 지금 수집
        </button>
      ))}
      {run.isPending && <span className="text-gray-400">수집 중… (요청 사이 2초씩 쉽니다)</span>}
      {msg && <span role="status">{msg}</span>}
    </span>
  )
}

function ReviewItem({ item, onDone }) {
  const { data: categories = [] } = useCategories()
  const { data: tags = [] } = useTags()
  const { data: venues = [] } = useVenues()
  const [open, setOpen] = useState(false)
  // 장소를 못 맞춘 항목은 관리자가 전시장을 고른다. 원본 장소 문자열을 별칭으로 저장하면 다음 수집부터 자동으로 맞춰진다
  const unmatched = !item.parsed_venue_id
  const [venueId, setVenueId] = useState('')
  const [saveAlias, setSaveAlias] = useState(true)
  const [alias, setAlias] = useState(item.raw_venue ?? '')
  const [error, setError] = useState('')
  const hall = item.raw_payload?.extra?.hall ?? ''
  const [form, setForm] = useState({
    title: item.raw_title,
    category: '',
    start_date: item.parsed_start_date ?? '',
    end_date: item.parsed_end_date ?? '',
    hall,
    public_access: 'unknown',
    price_onsite: '',
    price_prereg: '',
    official_url: item.detail_url ?? '',
    summary: '',
    visit_tip: '',
    tags: [],
    status: 'published',
    verified: true,
  })

  const act = useMutation({
    mutationFn: ({ kind, body }) => api.post(`/admin/crawled-items/${item.id}/${kind}`, body).then((r) => r.data),
    onSuccess: onDone,
    onError: (e) => setError(errorMessage(e)),
  })

  const approve = () => {
    const num = (v) => (v === '' ? null : Number(v))
    act.mutate({
      kind: 'approve',
      body: item.fair_id
        ? undefined
        : {
            ...form,
            venue_id: unmatched ? Number(venueId) : item.parsed_venue_id,
            venue_alias: unmatched && saveAlias && alias.trim() ? alias.trim() : null,
            price_onsite: num(form.price_onsite),
            price_prereg: num(form.price_prereg),
            official_url: form.official_url || null,
          },
    })
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const input = 'min-h-10 w-full rounded border px-2 text-sm'

  return (
    <li className="rounded-xl border p-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="text-sm">
          <p className="mb-1 text-xs font-semibold text-gray-500">
            원본 · {item.source} · {item.change_status === 'changed' ? '변경됨' : '신규'}
          </p>
          <p className="font-semibold">{item.raw_title}</p>
          <p>{item.raw_period}</p>
          <p>{item.raw_venue}</p>
          {item.detail_url && (
            <a href={item.detail_url} target="_blank" rel="noopener noreferrer" className="text-indigo-700 underline">
              원본 상세 보기
            </a>
          )}
        </div>
        <div className="text-sm">
          <p className="mb-1 text-xs font-semibold text-gray-500">정규화 결과</p>
          <p>기간: {item.parsed_start_date ? `${item.parsed_start_date} ~ ${item.parsed_end_date}` : <b className="text-red-600">읽지 못함 (직접 입력)</b>}</p>
          <p>장소: {item.parsed_venue_name ?? <b className="text-red-600">매칭 실패 (승인할 때 전시장 선택)</b>}</p>
          {item.fair_id && <p>연결된 박람회: <Link className="underline" to={`/admin/fairs/${item.fair_id}/edit`}>#{item.fair_id}</Link></p>}
          {item.merge_candidates.length > 0 && (
            <div className="mt-2 rounded bg-amber-50 p-2">
              <p className="font-semibold">병합 후보</p>
              {item.merge_candidates.map((c) => (
                <div key={c.fair_id} className="flex items-center justify-between gap-2">
                  <span>{c.title} ({c.start_date}) · 유사도 {c.similarity}</span>
                  <button type="button" className="rounded border px-2" onClick={() => act.mutate({ kind: 'merge', body: { fair_id: c.fair_id } })}>
                    병합
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {open && !item.fair_id && (
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <input className={`${input} sm:col-span-3`} value={form.title} onChange={set('title')} aria-label="제목" />
          {unmatched && (
            <div className="space-y-2 rounded bg-red-50 p-2 sm:col-span-3">
              <select className={input} value={venueId} onChange={(e) => setVenueId(e.target.value)} aria-label="전시장">
                <option value="">전시장 선택 (원본: {item.raw_venue || '없음'})</option>
                {venues.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.region})</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={saveAlias} onChange={(e) => setSaveAlias(e.target.checked)} />
                이 장소 이름을 별칭으로 저장 (다음 수집부터 자동으로 맞춤)
              </label>
              {saveAlias && (
                <input className={input} value={alias} onChange={(e) => setAlias(e.target.value)} maxLength={100} aria-label="별칭" />
              )}
              <p className="text-xs text-gray-500">별칭은 장소 이름의 앞부분만 남기세요. 뒤에 붙은 글자는 전시홀로 읽어요 (예: 별칭 '삼성동 컨벤션센터' → '삼성동 컨벤션센터 3층 E홀' 의 홀은 '3층 E홀')</p>
            </div>
          )}
          <select className={input} value={form.category} onChange={set('category')} aria-label="카테고리">
            <option value="">카테고리 선택</option>
            {categories.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
          <input type="date" className={input} value={form.start_date} onChange={set('start_date')} aria-label="시작일" />
          <input type="date" className={input} value={form.end_date} onChange={set('end_date')} aria-label="종료일" />
          <select className={input} value={form.public_access} onChange={set('public_access')} aria-label="일반인 관람">
            <option value="unknown">일반인 관람: 모름</option>
            <option value="public">일반인 관람 가능</option>
            <option value="partial">일부 날짜만</option>
            <option value="trade_only">업계 종사자 전용</option>
          </select>
          <input type="number" min={0} placeholder="현장 입장료(원)" className={input} value={form.price_onsite} onChange={set('price_onsite')} />
          <input type="number" min={0} placeholder="사전등록 입장료(원)" className={input} value={form.price_prereg} onChange={set('price_prereg')} />
          <textarea placeholder="소개 (직접 요약)" className={`${input} sm:col-span-3`} value={form.summary} onChange={set('summary')} />
          <textarea placeholder="관람 팁" className={`${input} sm:col-span-3`} value={form.visit_tip} onChange={set('visit_tip')} />
          <div className="flex flex-wrap gap-2 sm:col-span-3">
            {tags.map((t) => (
              <label key={t.slug} className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={form.tags.includes(t.slug)}
                  onChange={() => setForm({ ...form, tags: form.tags.includes(t.slug) ? form.tags.filter((x) => x !== t.slug) : [...form.tags, t.slug] })}
                />
                {t.name}
              </label>
            ))}
          </div>
        </div>
      )}

      {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {!item.fair_id && !open && (
          <button type="button" className="min-h-10 rounded bg-indigo-600 hover:bg-indigo-700 px-3 text-sm text-white" onClick={() => setOpen(true)}>
            정보 채우고 승인
          </button>
        )}
        {(open || item.fair_id) && (
          <button type="button" disabled={act.isPending || (!item.fair_id && (!form.category || (unmatched && !venueId)))} className="min-h-10 rounded bg-indigo-600 hover:bg-indigo-700 px-3 text-sm text-white disabled:opacity-50" onClick={approve}>
            {item.fair_id ? '변경 확인' : '승인해 공개'}
          </button>
        )}
        <button type="button" className="min-h-10 rounded border px-3 text-sm" onClick={() => act.mutate({ kind: 'reject' })}>
          반려
        </button>
      </div>
    </li>
  )
}

export function AdminCrawlRuns() {
  const { data } = useQuery({ queryKey: ['admin', 'runs'], queryFn: () => api.get('/admin/crawl-runs').then((r) => r.data) })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">수집 이력</h1>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-b text-gray-500">
            <tr>
              <th className="py-2">시작</th>
              <th>소스</th>
              <th>결과</th>
              <th>발견 / 신규 / 변경</th>
              <th>오류</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.id} className="border-b">
                <td className="py-2">{r.started_at.slice(0, 16).replace('T', ' ')}</td>
                <td>{r.source}</td>
                <td className={r.status === 'failed' ? 'text-red-600' : ''}>{r.status}</td>
                <td>{r.found_count} / {r.new_count} / {r.changed_count}</td>
                <td className="max-w-xs truncate" title={r.error_message ?? ''}>{r.error_message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

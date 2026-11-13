import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { createFair, fetchAdminFair, updateFair } from '../../api/admin'
import { errorMessage } from '../../api/client'
import { useCategories, useTags, useVenues } from '../../hooks/useFairs'

const EMPTY = {
  title: '',
  category: '',
  venue_id: '',
  hall: '',
  start_date: '',
  end_date: '',
  open_time: '',
  close_time: '',
  hours_note: '',
  public_access: 'unknown',
  access_note: '',
  price_onsite: '',
  price_prereg: '',
  prereg_start_at: '',
  prereg_end_at: '',
  prereg_url: '',
  official_url: '',
  summary: '',
  visit_tip: '',
  status: 'draft',
  tags: [],
  verified: false,
}

// 서버 값(+09:00 일시) → 폼 값(datetime-local)
function toForm(f) {
  const local = (iso) => (iso ? iso.slice(0, 16) : '')
  const out = { ...EMPTY }
  Object.keys(EMPTY).forEach((k) => {
    if (f[k] !== undefined && f[k] !== null) out[k] = f[k]
  })
  return { ...out, prereg_start_at: local(f.prereg_start_at), prereg_end_at: local(f.prereg_end_at), verified: false }
}

// 폼 값 → 요청 본문. 빈 칸은 null(모름)로 보낸다. 입장료 0 은 무료라 그대로 보낸다
function toBody(form) {
  const nul = (v) => (v === '' ? null : v)
  const num = (v) => (v === '' ? null : Number(v))
  const kst = (v) => (v ? `${v}:00+09:00` : null)
  return {
    ...form,
    venue_id: Number(form.venue_id),
    hall: nul(form.hall),
    open_time: nul(form.open_time),
    close_time: nul(form.close_time),
    hours_note: nul(form.hours_note),
    access_note: nul(form.access_note),
    price_onsite: num(form.price_onsite),
    price_prereg: num(form.price_prereg),
    prereg_start_at: kst(form.prereg_start_at),
    prereg_end_at: kst(form.prereg_end_at),
    prereg_url: nul(form.prereg_url),
    official_url: nul(form.official_url),
    summary: nul(form.summary),
    visit_tip: nul(form.visit_tip),
  }
}

// 관리자 박람회 등록·수정 (F-08). /admin/fairs/new, /admin/fairs/:fairId/edit
export default function AdminFairEdit() {
  const { fairId } = useParams()
  const isNew = !fairId
  const existing = useQuery({ queryKey: ['admin', 'fair', fairId], queryFn: () => fetchAdminFair(fairId), enabled: !isNew })

  if (!isNew && existing.isPending) return <p className="text-gray-400">불러오는 중…</p>
  if (!isNew && existing.isError) return <p className="text-red-600">{errorMessage(existing.error)}</p>
  // 박람회가 바뀌면(새로 만든 뒤 수정 화면으로 이동 등) key 로 폼을 새로 그린다
  return <FairForm key={fairId ?? 'new'} fairId={fairId} existing={existing.data} />
}

function FairForm({ fairId, existing }) {
  const isNew = !fairId
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: categories = [] } = useCategories()
  const { data: venues = [] } = useVenues()
  const { data: tags = [] } = useTags()
  const [form, setForm] = useState(() => (existing ? toForm(existing) : EMPTY))
  // 새로 등록하면 수정 화면으로 옮기며 폼을 새로 그리므로, '저장했어요' 는 이동 상태(state)로 넘겨 받는다
  const location = useLocation()
  const [message, setMessage] = useState(location.state?.saved ? '저장했어요' : '')

  const save = useMutation({
    mutationFn: () => (isNew ? createFair(toBody(form)) : updateFair(fairId, toBody(form))),
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ['admin'] })
      qc.invalidateQueries({ queryKey: ['fairs'] })
      qc.invalidateQueries({ queryKey: ['fair', String(saved.id)] })
      setMessage('저장했어요')
      if (isNew) navigate(`/admin/fairs/${saved.id}/edit`, { replace: true, state: { saved: true } })
      else setForm(toForm(saved))
    },
    onError: (err) => setMessage(errorMessage(err)),
  })

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const toggleTag = (slug) =>
    setForm({ ...form, tags: form.tags.includes(slug) ? form.tags.filter((t) => t !== slug) : [...form.tags, slug] })

  const input = 'min-h-11 w-full rounded-lg border border-gray-300 px-3'
  return (
    <form
      className="max-w-3xl space-y-6"
      onSubmit={(e) => {
        e.preventDefault()
        setMessage('')
        save.mutate()
      }}
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{isNew ? '새 박람회' : '박람회 수정'}</h1>
        <div className="flex gap-3 text-sm">
          {!isNew && form.status === 'published' && (
            <Link to={`/fairs/${fairId}`} className="underline">
              공개 화면 보기
            </Link>
          )}
          <Link to="/admin/fairs" className="underline">
            목록
          </Link>
        </div>
      </div>

      <Group title="기본 정보">
        <L label="제목"><input required maxLength={200} className={input} value={form.title} onChange={set('title')} /></L>
        <L label="카테고리">
          <select required className={input} value={form.category} onChange={set('category')}>
            <option value="">선택</option>
            {categories.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </L>
        <L label="전시장">
          <select required className={input} value={form.venue_id} onChange={set('venue_id')}>
            <option value="">선택</option>
            {venues.map((v) => <option key={v.id} value={v.id}>{v.name} ({v.region})</option>)}
          </select>
        </L>
        <L label="전시홀"><input className={input} value={form.hall} onChange={set('hall')} placeholder="예: A홀" /></L>
        <L label="시작일"><input required type="date" className={input} value={form.start_date} onChange={set('start_date')} /></L>
        <L label="종료일"><input required type="date" className={input} value={form.end_date} onChange={set('end_date')} /></L>
        <L label="개장 시간"><input type="time" className={input} value={form.open_time?.slice(0, 5) ?? ''} onChange={set('open_time')} /></L>
        <L label="폐장 시간"><input type="time" className={input} value={form.close_time?.slice(0, 5) ?? ''} onChange={set('close_time')} /></L>
        <L label="운영 시간 메모" wide><input className={input} value={form.hours_note} onChange={set('hours_note')} placeholder="예: 마지막 날 16시 마감" /></L>
      </Group>

      <Group title="관람 조건">
        <L label="일반인 관람">
          <select className={input} value={form.public_access} onChange={set('public_access')}>
            <option value="public">일반인 관람 가능</option>
            <option value="partial">일부 날짜만</option>
            <option value="trade_only">업계 종사자 전용</option>
            <option value="unknown">모름</option>
          </select>
        </L>
        <L label="관람 조건 메모"><input className={input} value={form.access_note} onChange={set('access_note')} placeholder="예: 일반인은 주말만 입장" /></L>
        <L label="현장 입장료(원, 비우면 미확인 · 0은 무료)"><input type="number" min={0} className={input} value={form.price_onsite} onChange={set('price_onsite')} /></L>
        <L label="사전등록 입장료(원)"><input type="number" min={0} className={input} value={form.price_prereg} onChange={set('price_prereg')} /></L>
        <L label="사전등록 시작 (한국 시간)"><input type="datetime-local" className={input} value={form.prereg_start_at} onChange={set('prereg_start_at')} /></L>
        <L label="사전등록 마감 (한국 시간)"><input type="datetime-local" className={input} value={form.prereg_end_at} onChange={set('prereg_end_at')} /></L>
        <L label="사전등록 페이지" wide><input type="url" className={input} value={form.prereg_url} onChange={set('prereg_url')} /></L>
        <L label="공식 홈페이지" wide><input type="url" className={input} value={form.official_url} onChange={set('official_url')} /></L>
      </Group>

      <Group title="큐레이션">
        <L label="소개 (원문 복제 금지, 직접 요약)" wide>
          <textarea rows={4} className={`${input} py-2`} value={form.summary} onChange={set('summary')} />
        </L>
        <L label="관람 팁 (주차, 붐비는 시간, 추천 동선)" wide>
          <textarea rows={3} className={`${input} py-2`} value={form.visit_tip} onChange={set('visit_tip')} />
        </L>
        <fieldset className="sm:col-span-2">
          <legend className="mb-1 text-sm text-gray-700">태그</legend>
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => (
              <label key={t.slug} className="flex min-h-11 items-center gap-1.5 rounded-lg border px-3 text-sm">
                <input type="checkbox" checked={form.tags.includes(t.slug)} onChange={() => toggleTag(t.slug)} />
                {t.name}
              </label>
            ))}
          </div>
        </fieldset>
      </Group>

      <Group title="공개">
        <L label="상태">
          <select className={input} value={form.status} onChange={set('status')}>
            <option value="draft">초안</option>
            <option value="published">공개</option>
            <option value="hidden">숨김</option>
          </select>
        </L>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={form.verified} onChange={set('verified')} />
          공식 사이트에서 정보를 확인했어요 (정보 확인일을 오늘로 기록)
        </label>
        {existing?.verified_at && (
          <p className="text-sm text-gray-500 sm:col-span-2">마지막 정보 확인: {existing.verified_at.slice(0, 16).replace('T', ' ')}</p>
        )}
      </Group>

      {message && <p role="status" className="text-sm">{message}</p>}
      <button disabled={save.isPending} className="min-h-11 rounded-lg bg-indigo-600 px-6 text-white disabled:opacity-60">
        {save.isPending ? '저장 중…' : '저장'}
      </button>
    </form>
  )
}

function Group({ title, children }) {
  return (
    <fieldset className="grid gap-3 rounded-xl border p-4 sm:grid-cols-2">
      <legend className="px-1 font-semibold">{title}</legend>
      {children}
    </fieldset>
  )
}

function L({ label, wide, children }) {
  return (
    <label className={`block space-y-1 ${wide ? 'sm:col-span-2' : ''}`}>
      <span className="text-sm text-gray-700">{label}</span>
      {children}
    </label>
  )
}

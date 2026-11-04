import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { errorMessage } from '../api/client'
import * as eng from '../api/engagement'
import { useAuth } from '../store/AuthContext'

function LoginHint({ text }) {
  const location = useLocation()
  return (
    <Link to={`/login?next=${encodeURIComponent(location.pathname)}`} className="text-sm text-indigo-700 underline">
      {text}
    </Link>
  )
}

// 태그 투표 (F-16): '데이트 추천' 같은 태그에 투표. 3표 이상이면 태그로 붙는다
export function TagVotes({ fairId }) {
  const { user } = useAuth()
  const qc = useQueryClient()
  const { data: rows = [] } = useQuery({ queryKey: ['tag-votes', fairId], queryFn: () => eng.fetchTagVotes(fairId) })
  const vote = useMutation({
    mutationFn: ({ tagId, on }) => eng.setTagVote(fairId, tagId, on),
    onSuccess: (data) => {
      qc.setQueryData(['tag-votes', fairId], data)
      qc.invalidateQueries({ queryKey: ['fair', String(fairId)] })
    },
  })
  if (rows.length === 0) return null
  return (
    <section className="space-y-2">
      <h2 className="font-semibold">이 박람회, 이런가요?</h2>
      <div className="flex flex-wrap gap-2">
        {rows.map((r) => (
          <button
            key={r.tag_id}
            type="button"
            aria-pressed={r.voted}
            disabled={!user || vote.isPending}
            onClick={() => vote.mutate({ tagId: r.tag_id, on: !r.voted })}
            className={`min-h-11 rounded-full border px-4 text-sm ${r.voted ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-gray-300'}`}
          >
            #{r.name} {r.vote_count > 0 && <span className="text-gray-500">{r.vote_count}</span>}
          </button>
        ))}
      </div>
      {!user && <LoginHint text="로그인하고 투표하기" />}
    </section>
  )
}

// 관람 노트 (F-14): 다녀옴 체크, 별점, 메모, 공개 여부
export function MyVisit({ fairId }) {
  const { user } = useAuth()
  const qc = useQueryClient()
  const { data: visits } = useQuery({ queryKey: ['my-visits'], queryFn: eng.fetchMyVisits, enabled: !!user })
  const mine = visits?.find((v) => v.fair_id === Number(fairId))
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')

  const save = useMutation({
    mutationFn: (body) => (mine ? eng.updateVisit(mine.id, body) : eng.createVisit(fairId, body)),
    onSuccess: () => {
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['my-visits'] })
      qc.invalidateQueries({ queryKey: ['reviews', fairId] })
    },
    onError: (e) => setError(errorMessage(e)),
  })
  const remove = useMutation({
    mutationFn: () => eng.deleteVisit(mine.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-visits'] })
      qc.invalidateQueries({ queryKey: ['reviews', fairId] })
    },
  })

  if (!user) return <section className="rounded-xl border p-4"><LoginHint text="로그인하고 관람 노트 남기기" /></section>

  const start = () => {
    setForm({
      visited_on: mine?.visited_on ?? '',
      rating: mine?.rating ?? '',
      memo: mine?.memo ?? '',
      is_public: mine?.is_public ?? false,
    })
    setError('')
    setEditing(true)
  }

  if (!editing) {
    return (
      <section className="rounded-xl border p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">내 관람 노트</h2>
          <button type="button" onClick={start} className="min-h-11 rounded-lg border px-3 text-sm">
            {mine ? '고치기' : '다녀왔어요'}
          </button>
        </div>
        {mine && (
          <div className="mt-2 text-sm text-gray-700">
            <p>{mine.visited_on ?? '날짜 미입력'} · {mine.rating ? '★'.repeat(mine.rating) : '별점 없음'} · {mine.is_public ? '공개' : '나만 보기'}</p>
            {mine.memo && <p className="mt-1 whitespace-pre-line">{mine.memo}</p>}
          </div>
        )}
      </section>
    )
  }

  return (
    <form
      className="space-y-3 rounded-xl border p-4"
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate({
          visited_on: form.visited_on || null,
          rating: form.rating === '' ? null : Number(form.rating),
          memo: form.memo || null,
          is_public: form.is_public,
        })
      }}
    >
      <h2 className="font-semibold">내 관람 노트</h2>
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          다녀온 날 <input type="date" className="ml-1 min-h-11 rounded border px-2" value={form.visited_on} onChange={(e) => setForm({ ...form, visited_on: e.target.value })} />
        </label>
        <label className="text-sm">
          별점{' '}
          <select className="ml-1 min-h-11 rounded border px-2" value={form.rating} onChange={(e) => setForm({ ...form, rating: e.target.value })}>
            <option value="">선택 안 함</option>
            {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{'★'.repeat(n)}</option>)}
          </select>
        </label>
      </div>
      <textarea
        rows={3}
        maxLength={2000}
        placeholder="주차, 붐빈 시간, 꼭 볼 부스… 다녀온 기록을 남겨 보세요"
        className="w-full rounded border p-2 text-sm"
        value={form.memo}
        onChange={(e) => setForm({ ...form, memo: e.target.value })}
      />
      <label className="flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={form.is_public} onChange={(e) => setForm({ ...form, is_public: e.target.checked })} />
        후기로 공개하기 (닉네임이 함께 보여요)
      </label>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button disabled={save.isPending} className="min-h-11 rounded-lg bg-indigo-600 px-4 text-sm text-white">저장</button>
        <button type="button" onClick={() => setEditing(false)} className="min-h-11 rounded-lg border px-4 text-sm">취소</button>
        {mine && (
          <button type="button" onClick={() => window.confirm('관람 노트를 지울까요?') && remove.mutate()} className="ml-auto min-h-11 px-2 text-sm text-red-600">
            삭제
          </button>
        )}
      </div>
    </form>
  )
}

// 후기 (F-15): 공개된 관람 노트와 좋아요
export function Reviews({ fairId }) {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const { data } = useQuery({ queryKey: ['reviews', fairId, page], queryFn: () => eng.fetchReviews(fairId, page) })
  const like = useMutation({
    mutationFn: ({ id, on }) => eng.setLike(id, on),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reviews', fairId] }),
  })
  if (!data) return null
  return (
    <section className="space-y-3">
      <h2 className="font-semibold">
        후기 {data.total}개{data.rating_avg != null && <span className="ml-2 text-sm font-normal text-amber-600">★ {data.rating_avg} ({data.rating_count})</span>}
      </h2>
      {data.items.length === 0 && <p className="text-sm text-gray-500">아직 공개된 후기가 없어요</p>}
      <ul className="space-y-3">
        {data.items.map((r) => (
          <li key={r.id} className="rounded-xl border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">{r.nickname}{r.is_mine && ' (나)'}</span>
              <span className="text-gray-500">{r.rating ? '★'.repeat(r.rating) : ''} {r.visited_on ?? ''}</span>
            </div>
            {r.memo && <p className="mt-1 whitespace-pre-line text-gray-700">{r.memo}</p>}
            <button
              type="button"
              disabled={!user || like.isPending}
              aria-pressed={r.liked_by_me}
              onClick={() => like.mutate({ id: r.id, on: !r.liked_by_me })}
              className={`mt-2 min-h-9 rounded-full border px-3 text-xs ${r.liked_by_me ? 'border-rose-400 text-rose-600' : 'text-gray-600'}`}
            >
              ♥ {r.like_count}
            </button>
          </li>
        ))}
      </ul>
      {data.total > data.size && (
        <div className="flex gap-2">
          <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} className="min-h-11 rounded border px-3 text-sm">이전</button>
          <button type="button" disabled={page * data.size >= data.total} onClick={() => setPage(page + 1)} className="min-h-11 rounded border px-3 text-sm">다음</button>
        </div>
      )}
    </section>
  )
}

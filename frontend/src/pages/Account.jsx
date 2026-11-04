import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import * as eng from '../api/engagement'
import { useAuth } from '../store/AuthContext'
import { AuthCard, Field } from './Login'

// 내 관람 노트 (/mypage/visits)
export function MyVisits() {
  const { data = [], isPending } = useQuery({ queryKey: ['my-visits'], queryFn: eng.fetchMyVisits })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">관람 노트</h1>
      {isPending && <p className="text-gray-400">불러오는 중…</p>}
      {!isPending && data.length === 0 && (
        <p className="rounded-xl border border-dashed p-8 text-center text-gray-500">다녀온 박람회의 상세 페이지에서 '다녀왔어요'를 눌러 기록해 보세요</p>
      )}
      <ul className="space-y-3">
        {data.map((v) => (
          <li key={v.id} className="rounded-xl border p-4 text-sm">
            <Link to={`/fairs/${v.fair_id}`} className="font-semibold text-indigo-700 underline">{v.fair_title}</Link>
            <p className="text-gray-500">{v.visited_on ?? '날짜 미입력'} · {v.rating ? '★'.repeat(v.rating) : '별점 없음'} · {v.is_public ? `공개 · ♥ ${v.like_count}` : '나만 보기'}</p>
            {v.memo && <p className="mt-1 whitespace-pre-line">{v.memo}</p>}
          </li>
        ))}
      </ul>
    </div>
  )
}

const KINDS = [
  ['prereg_deadline', '사전등록 마감 하루 전'],
  ['opening_soon', '개막 3일 전'],
  ['fair_updated', '북마크한 박람회의 기간·장소·사전등록 정보 변경'],
]

// 알림 설정 (F-12). Settings 페이지 안에 들어간다
export function NotificationSettings() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['notification-settings'], queryFn: eng.fetchNotificationSettings })
  const save = useMutation({
    mutationFn: eng.saveNotificationSettings,
    onSuccess: (d) => qc.setQueryData(['notification-settings'], d),
  })
  if (!data) return null
  if (!user?.email) {
    return (
      <section className="space-y-2 rounded-xl border p-4">
        <h2 className="font-semibold">알림 메일</h2>
        <p className="text-sm text-gray-500">이메일 없이 소셜 계정으로 가입해서 알림 메일을 받을 수 없어요.</p>
      </section>
    )
  }
  const toggle = (k) => save.mutate({ ...data, [k]: !data[k] })
  return (
    <section className="space-y-2 rounded-xl border p-4">
      <h2 className="font-semibold">알림 메일</h2>
      <p className="text-sm text-gray-500">북마크한 박람회 소식을 매일 오전 9시에 메일로 보내 드려요.</p>
      <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={data.email_enabled} onChange={() => toggle('email_enabled')} />
        알림 메일 받기
      </label>
      {KINDS.map(([k, label]) => (
        <label key={k} className="ml-6 flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" disabled={!data.email_enabled} checked={data[k]} onChange={() => toggle(k)} />
          {label}
        </label>
      ))}
    </section>
  )
}

// 비밀번호 재설정 (/reset-password). 메일 링크로 들어오면 ?token= 이 있다
export function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token')
  return token ? <ResetConfirm token={token} /> : <ResetRequest />
}

function ResetRequest() {
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  return (
    <AuthCard title="비밀번호 재설정">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault()
          setBusy(true)
          try {
            setMsg((await eng.requestPasswordReset(email)).message)
          } catch (err) {
            setMsg(errorMessage(err))
          } finally {
            setBusy(false)
          }
        }}
      >
        <Field label="가입한 이메일" type="email" value={email} onChange={setEmail} autoComplete="email" />
        {msg && <p role="status" className="text-sm text-gray-700">{msg}</p>}
        <button disabled={busy} className="min-h-11 w-full rounded-lg bg-indigo-600 text-white">재설정 링크 받기</button>
      </form>
    </AuthCard>
  )
}

function ResetConfirm({ token }) {
  const navigate = useNavigate()
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  return (
    <AuthCard title="새 비밀번호">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault()
          if (pw.length < 8) return setError('비밀번호는 8자 이상이어야 해요')
          try {
            await eng.confirmPasswordReset(token, pw)
            navigate('/login', { replace: true })
          } catch (err) {
            setError(errorMessage(err))
          }
        }}
      >
        <Field label="새 비밀번호 (8자 이상)" type="password" minLength={8} value={pw} onChange={setPw} autoComplete="new-password" />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button className="min-h-11 w-full rounded-lg bg-indigo-600 text-white">비밀번호 바꾸기</button>
      </form>
    </AuthCard>
  )
}

// 알림 메일의 수신 거부 링크 (/unsubscribe?token=). 링크 미리보기로 잘못 거부되지 않게 버튼을 눌러야 처리한다
export function Unsubscribe() {
  const [params] = useSearchParams()
  const [msg, setMsg] = useState('')
  const run = async () => {
    try {
      setMsg((await eng.unsubscribe(params.get('token') ?? '')).message)
    } catch (err) {
      setMsg(errorMessage(err))
    }
  }
  return (
    <AuthCard title="알림 메일 수신 거부">
      {msg ? (
        <p role="status" className="text-center text-gray-700">{msg}</p>
      ) : (
        <button type="button" onClick={run} className="min-h-11 w-full rounded-lg bg-gray-900 text-white">
          알림 메일 그만 받기
        </button>
      )}
    </AuthCard>
  )
}

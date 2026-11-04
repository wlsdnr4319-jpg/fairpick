import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { signup } from '../api/auth'
import { errorMessage } from '../api/client'
import SocialButtons, { oauthErrorMessage } from '../components/SocialButtons'
import { useAuth } from '../store/AuthContext'
import { AuthCard, Field } from './Login'

export default function Signup() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ email: '', password: '', nickname: '', is_over_14: false })
  const [error, setError] = useState(() => oauthErrorMessage(params.get('oauth_error')))
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (form.password.length < 8) return setError('비밀번호는 8자 이상이어야 해요')
    if (!form.is_over_14) return setError('만 14세 이상만 가입할 수 있어요')
    setBusy(true)
    setError('')
    try {
      await signup(form)
      await login(form.email, form.password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard title="회원가입">
      <form onSubmit={submit} className="space-y-3">
        <Field label="이메일" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} autoComplete="email" />
        <Field
          label="비밀번호 (8자 이상)"
          type="password"
          minLength={8}
          value={form.password}
          onChange={(v) => setForm({ ...form, password: v })}
          autoComplete="new-password"
        />
        <Field label="닉네임" maxLength={30} value={form.nickname} onChange={(v) => setForm({ ...form, nickname: v })} />
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_over_14} onChange={(e) => setForm({ ...form, is_over_14: e.target.checked })} />
          만 14세 이상입니다
        </label>
        <p className="text-xs text-gray-500">
          가입하면 <Link to="/terms" className="underline">이용약관</Link>과{' '}
          <Link to="/privacy" className="underline">개인정보 처리방침</Link>에 동의한 것으로 봅니다. 수집 항목은 이메일과 닉네임뿐이에요 (소셜 가입은 제공자가 주는 이메일·닉네임).
        </p>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button disabled={busy} className="min-h-11 w-full rounded-lg bg-indigo-600 text-white disabled:opacity-60">
          {busy ? '가입 중…' : '가입하기'}
        </button>
      </form>
      <SocialButtons signup disabled={!form.is_over_14} />
      {!form.is_over_14 && (
        <p className="text-center text-xs text-gray-500">소셜 계정으로 가입하려면 먼저 '만 14세 이상입니다'에 체크해 주세요</p>
      )}
    </AuthCard>
  )
}

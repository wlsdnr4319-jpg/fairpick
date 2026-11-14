import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import SocialButtons, { oauthErrorMessage } from '../components/SocialButtons'
import { useAuth } from '../store/AuthContext'
import { safeNext } from '../utils/nav'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(() => oauthErrorMessage(params.get('oauth_error')))
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(form.email, form.password)
      navigate(safeNext(params.get('next')), { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard title="로그인">
      <form onSubmit={submit} className="space-y-3">
        <Field label="이메일" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} autoComplete="email" />
        <Field label="비밀번호" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} autoComplete="current-password" />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button disabled={busy} className="min-h-11 w-full rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60">
          {busy ? '로그인 중…' : '로그인'}
        </button>
      </form>
      <SocialButtons next={safeNext(params.get('next'))} />
      <p className="text-center text-sm text-gray-600">
        <Link to="/reset-password" className="text-gray-500 underline">비밀번호를 잊으셨나요?</Link>
      </p>
      <p className="text-center text-sm text-gray-600">
        처음이신가요? <Link to="/signup" className="text-indigo-600">회원가입</Link>
      </p>
    </AuthCard>
  )
}

export function AuthCard({ title, children }) {
  return (
    <section className="mx-auto max-w-sm space-y-6 py-8">
      <h1 className="text-center text-2xl font-bold">{title}</h1>
      {children}
    </section>
  )
}

export function Field({ label, onChange, ...props }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-gray-700">{label}</span>
      <input
        required
        // 이메일·비밀번호는 맞춤법 검사 밑줄이 뜨지 않게
        spellCheck={props.type === 'email' || props.type === 'password' ? false : undefined}
        {...props}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-11 w-full rounded-lg border border-gray-300 px-3"
      />
    </label>
  )
}

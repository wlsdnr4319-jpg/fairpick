import { useEffect, useId, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useFairs } from '../hooks/useFairs'
import { useAuth } from '../store/AuthContext'

// 위쪽 바 (모든 화면). 휴대폰: ☰ · 로고 · 검색 · 계정 / 넓은 화면: 검색창 · 이번 주말 바로가기 · 계정.
// 로그인·회원가입과 계정 메뉴는 오른쪽 위에 둔다 (사이드바 아래에 있던 것을 옮김).
export default function TopBar({ menuButtonRef, menuOpen, onOpenMenu }) {
  const { user, ready } = useAuth()
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-1 border-b border-gray-200 bg-white/95 px-2 backdrop-blur md:h-16 md:gap-4 md:px-8">
      <button
        ref={menuButtonRef}
        type="button"
        onClick={onOpenMenu}
        aria-label="메뉴 열기"
        aria-expanded={menuOpen}
        aria-controls="mobile-menu"
        className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-700 hover:bg-gray-100 md:hidden"
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>
      <Link to="/" translate="no" className="mr-auto rounded-md px-1 text-lg font-bold text-indigo-600 md:hidden">
        페어픽
      </Link>

      <SearchBox />
      <WeekendLink />

      <Link
        to="/fairs"
        aria-label="검색"
        className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-700 hover:bg-gray-100 md:hidden"
      >
        <SearchIcon className="h-5 w-5" />
      </Link>

      {ready && !user && (
        <div className="flex items-center gap-1 md:ml-auto md:gap-2">
          <Link to="/login" className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm text-gray-700 hover:bg-gray-100">
            로그인
          </Link>
          <Link
            to="/signup"
            className="inline-flex min-h-10 items-center rounded-lg bg-indigo-600 px-3 text-sm font-medium text-white hover:bg-indigo-700 md:px-4"
          >
            회원가입
          </Link>
        </div>
      )}
      {ready && user && <AccountMenu user={user} />}
    </header>
  )
}

function SearchIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4" />
    </svg>
  )
}

// 어느 화면에서든 바로 검색 (넓은 화면만. 휴대폰은 돋보기 아이콘이 목록 화면으로 간다)
function SearchBox() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  return (
    <form
      role="search"
      aria-label="빠른 검색"
      className="relative hidden max-w-md flex-1 md:block"
      onSubmit={(e) => {
        e.preventDefault()
        const word = q.trim()
        navigate(word ? `/fairs?q=${encodeURIComponent(word)}` : '/fairs')
        setQ('')
      }}
    >
      <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="박람회 검색 (커피, 캠핑, 웨딩…)"
        aria-label="박람회 이름·키워드"
        className="h-10 w-full rounded-full border border-gray-200 bg-gray-50 pr-4 pl-9 text-sm focus:border-indigo-300 focus:bg-white"
      />
    </form>
  )
}

// 이번 주말에 열리는 박람회 수 (넓은 화면). 눌러서 바로 그 목록으로
function WeekendLink() {
  const { data } = useFairs({ period: 'this_weekend', size: 1 })
  if (!data) return <span className="hidden flex-1 lg:block" />
  return (
    <span className="hidden flex-1 lg:block">
      <Link
        to="/fairs?period=this_weekend"
        className="inline-flex min-h-10 items-center gap-2 rounded-full bg-amber-50 px-3 text-sm text-amber-900 hover:bg-amber-100"
      >
        <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden="true" />
        이번 주말 박람회 <strong className="font-semibold">{data.total}개</strong>
      </Link>
    </span>
  )
}

const MY_LINKS = [
  { to: '/mypage', label: '북마크' },
  { to: '/mypage/visits', label: '관람 노트' },
  { to: '/mypage/settings', label: '알림 설정' },
]

// 계정 메뉴: 버튼을 누르면 펼쳐지는 목록 (disclosure). Esc·바깥 누르기·이동으로 닫힌다
function AccountMenu({ user }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const id = useId()
  const button = useRef(null)
  const box = useRef(null)
  // 연 주소를 기억해서 페이지를 옮기면 저절로 닫히게 (서랍과 같은 방식)
  const [openedAt, setOpenedAt] = useState(null)
  const open = openedAt === location.key

  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => {
      if (!box.current?.contains(e.target)) setOpenedAt(null)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpenedAt(null)
        button.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const links = user.role === 'admin' ? [...MY_LINKS, { to: '/admin', label: '관리자 홈' }] : MY_LINKS
  return (
    <div ref={box} className="relative md:ml-auto">
      <button
        ref={button}
        type="button"
        onClick={() => setOpenedAt(open ? null : location.key)}
        aria-expanded={open}
        aria-controls={id}
        aria-label={`계정 메뉴 (${user.nickname})`}
        className="inline-flex min-h-11 items-center gap-2 rounded-full py-1 pr-1 pl-1 hover:bg-gray-100 md:pr-3"
      >
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700" aria-hidden="true">
          {[...user.nickname][0]}
        </span>
        <span className="hidden max-w-32 truncate text-sm font-medium text-gray-800 md:inline">{user.nickname}</span>
        <svg viewBox="0 0 24 24" className="hidden h-4 w-4 text-gray-500 md:block" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div id={id} className="absolute top-full right-0 mt-2 w-56 animate-[fade-in_120ms_ease-out] rounded-xl border bg-white p-1 shadow-lg">
          <p className="truncate px-3 py-2 text-sm">
            <span className="font-semibold">{user.nickname}</span>님
            <span className="block truncate text-xs text-gray-500">{user.email}</span>
          </p>
          <ul className="border-t pt-1">
            {links.map((l) => (
              <li key={l.to}>
                <Link to={l.to} className="flex min-h-10 items-center rounded-lg px-3 text-sm text-gray-700 hover:bg-gray-100">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-1 border-t pt-1">
            <button
              type="button"
              onClick={() => {
                // 로그아웃하면 이 메뉴가 사라져(로그인 버튼으로 바뀜) 그 뒤의 이동이 무시된다. 먼저 홈으로 옮기고 로그아웃
                setOpenedAt(null)
                navigate('/')
                logout()
              }}
              className="flex min-h-10 w-full items-center rounded-lg px-3 text-left text-sm text-gray-700 hover:bg-gray-100"
            >
              로그아웃
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

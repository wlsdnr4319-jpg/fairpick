import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useCategories } from '../hooks/useFairs'
import { useAuth } from '../store/AuthContext'
import { activeLink } from '../utils/nav'

// 사이드바 메뉴 (데스크톱은 왼쪽 고정, 휴대폰은 ☰ 로 여는 서랍). 같은 내용을 Layout 이 두 곳에 그린다.
// 자주 쓰는 목록(이번 주말·마감 임박·카테고리)은 필터 주소로 바로 가게 해서 필터를 매번 고르지 않아도 된다.

const BROWSE = [
  { to: '/', label: '홈', icon: 'home' },
  { to: '/fairs', label: '박람회 찾기', icon: 'search' },
  { to: '/fairs?period=this_weekend', label: '이번 주말', icon: 'sun' },
  { to: '/fairs?sort=prereg_deadline', label: '사전등록 마감 임박', icon: 'clock' },
  { to: '/calendar', label: '캘린더', icon: 'calendar' },
  { to: '/report', label: '통계', icon: 'chart' },
]
const MINE = [
  { to: '/mypage', label: '북마크', icon: 'bookmark' },
  { to: '/mypage/visits', label: '관람 노트', icon: 'note' },
  { to: '/mypage/settings', label: '알림 설정', icon: 'bell' },
]
const ADMIN = [
  { to: '/admin', label: '관리자 홈', icon: 'shield' },
  { to: '/admin/fairs', label: '박람회 관리', icon: 'list' },
  { to: '/admin/review', label: '수집 검수', icon: 'inbox' },
]

// account: 아래쪽 닉네임·로그아웃(로그인 전엔 로그인·회원가입). 넓은 화면은 위쪽 바 오른쪽에 있어서 휴대폰 서랍에서만 켠다
export default function Sidebar({ onNavigate, account = false }) {
  const { user, ready, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { data: categories = [] } = useCategories()

  const cats = categories.map((c) => ({ to: `/fairs?category=${c.code}`, label: c.name, icon: 'tag' }))
  const all = [...BROWSE, ...cats, ...(user ? MINE : []), ...(user?.role === 'admin' ? ADMIN : [])]
  const active = activeLink(
    all.map((l) => l.to),
    location,
  )

  return (
    <div className="flex h-full flex-col">
      {/* 높이·아래 선을 위쪽 바(h-16)와 맞춰 한 줄로 이어 보이게 */}
      <div className="mb-4 flex h-14 shrink-0 items-center border-b border-gray-200 px-3 md:h-16">
        <Link to="/" translate="no" onClick={onNavigate} className="rounded-md px-2 text-xl font-bold text-indigo-600">
          페어픽
        </Link>
      </div>

      <nav aria-label="사이드바" className="flex-1 space-y-5 overflow-y-auto overscroll-contain px-3 pb-4">
        <Section title="둘러보기" links={BROWSE} active={active} onNavigate={onNavigate} />
        {cats.length > 0 && <Section title="카테고리" links={cats} active={active} onNavigate={onNavigate} compact />}
        {ready && user && <Section title="내 페어픽" links={MINE} active={active} onNavigate={onNavigate} />}
        {ready && user?.role === 'admin' && <Section title="관리" links={ADMIN} active={active} onNavigate={onNavigate} />}
      </nav>

      {account && (
        <div className="border-t border-gray-200 p-3">
          {ready && user && (
            <div className="flex items-center gap-2">
              <p className="min-w-0 flex-1 truncate px-2 text-sm text-gray-700">
                <span className="font-semibold">{user.nickname}</span>님
              </p>
              <button
                type="button"
                onClick={async () => {
                  await logout()
                  onNavigate?.()
                  navigate('/')
                }}
                className="inline-flex min-h-11 items-center rounded-md px-3 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              >
                로그아웃
              </button>
            </div>
          )}
          {ready && !user && (
            <div className="flex gap-2">
              <Link
                to="/login"
                onClick={onNavigate}
                className="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg bg-indigo-600 text-sm text-white hover:bg-indigo-700"
              >
                로그인
              </Link>
              <Link
                to="/signup"
                onClick={onNavigate}
                className="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg border text-sm text-gray-700 hover:bg-gray-50"
              >
                회원가입
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ title, links, active, onNavigate, compact = false }) {
  return (
    <section>
      <h2 className="mb-1 px-2 text-xs font-semibold text-gray-500">{title}</h2>
      <ul className={compact ? 'flex flex-wrap gap-1.5 px-1' : 'space-y-0.5'}>
        {links.map((l) => {
          const current = l.to === active
          if (compact) {
            return (
              <li key={l.to}>
                <Link
                  to={l.to}
                  onClick={onNavigate}
                  aria-current={current ? 'page' : undefined}
                  className={`inline-flex min-h-9 items-center rounded-full px-3 text-sm ${
                    current ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-700'
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            )
          }
          return (
            <li key={l.to}>
              <Link
                to={l.to}
                onClick={onNavigate}
                aria-current={current ? 'page' : undefined}
                className={`flex min-h-11 items-center gap-3 rounded-lg px-2 text-sm ${
                  current ? 'bg-indigo-50 font-semibold text-indigo-700' : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <Icon name={l.icon} />
                {l.label}
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// 24x24 선 아이콘 (라이브러리 없이 필요한 것만). 글자와 함께 쓰므로 스크린리더에는 숨긴다
const PATHS = {
  home: 'M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  bookmark: 'M6 3h12v18l-6-4-6 4z',
  note: 'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h6',
  bell: 'M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 21h4',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  inbox: 'M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6z',
}

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  )
}

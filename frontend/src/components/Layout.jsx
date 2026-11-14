import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

// 데스크톱(md 이상)은 왼쪽 고정 사이드바, 휴대폰은 위쪽 바의 ☰ 로 여는 서랍. 위쪽 바(TopBar)는 검색·로그인·계정 메뉴.
// 서랍은 열 때만 그려서(조건부 렌더) 같은 링크가 화면에 두 번 잡히지 않게 한다.
export default function Layout() {
  const location = useLocation()
  // 서랍을 연 주소(location.key)를 기억한다. 페이지를 옮기면(링크·뒤로 가기) key 가 바뀌어 저절로 닫힌다
  const [openedAt, setOpenedAt] = useState(null)
  const open = openedAt === location.key
  const setOpen = useCallback((value) => setOpenedAt(value ? location.key : null), [location.key])
  const menuButton = useRef(null)

  // Esc·바깥·닫기 버튼으로 닫으면 포커스를 ☰ 버튼으로 돌려준다. 링크로 이동할 때는 새 페이지라 돌리지 않는다
  const dismiss = useCallback(() => {
    setOpenedAt(null)
    menuButton.current?.focus()
  }, [])
  const navigated = useCallback(() => setOpenedAt(null), [])

  return (
    <div className="min-h-screen bg-white text-gray-900 md:flex">
      {/* 키보드 사용자가 메뉴를 건너뛰고 본문으로 바로 가는 링크. 포커스를 받을 때만 보인다 */}
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-indigo-600 px-4 py-2 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-3"
      >
        본문으로 건너뛰기
      </a>

      <aside className="hidden shrink-0 border-r border-gray-200 bg-gray-50/60 md:sticky md:top-0 md:block md:h-screen md:w-60">
        <Sidebar />
      </aside>


      {open && <Drawer onClose={dismiss} onNavigate={navigated} />}

      {/* 서랍이 열려 있는 동안 뒤쪽 화면은 포커스·클릭이 닿지 않게(inert) */}
      <div className="flex min-w-0 flex-1 flex-col" inert={open || undefined}>
        <TopBar menuButtonRef={menuButton} menuOpen={open} onOpenMenu={() => setOpen(true)} />
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 outline-none md:px-8">
          <Outlet />
        </main>

        {/* 정보 정확성 안내와 법적 고지 (레퍼런스 15장) */}
        <footer className="border-t border-gray-200 py-6 text-center text-xs text-gray-500">
          <p>일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.</p>
          <p className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1">
            <Link to="/privacy" className="font-semibold underline hover:text-gray-800">
              개인정보 처리방침
            </Link>
            <Link to="/terms" className="underline hover:text-gray-800">
              이용약관
            </Link>
            <Link to="/credits" className="underline hover:text-gray-800">
              사진 출처
            </Link>
            <a href="mailto:contact@example.com" className="underline hover:text-gray-800">
              정보 수정·삭제 요청
            </a>
          </p>
        </footer>
      </div>
    </div>
  )
}

// 휴대폰 메뉴 서랍: Esc·바깥 누르기로 닫힘, 열린 동안 뒤 화면 스크롤 막음, 열면 닫기 버튼으로 포커스
function Drawer({ onClose, onNavigate }) {
  const panel = useRef(null)

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    panel.current?.querySelector('a, button')?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
      // 포커스가 서랍 밖으로 나가지 않게 Tab 을 처음·끝에서 돌린다
      if (e.key === 'Tab' && panel.current) {
        const items = [...panel.current.querySelectorAll('a[href], button:not([disabled])')]
        const first = items[0]
        const last = items.at(-1)
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <div className="absolute inset-0 animate-[fade-in_150ms_ease-out] bg-gray-900/40" onClick={onClose} aria-hidden="true" />
      <div
        id="mobile-menu"
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label="메뉴"
        className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] animate-[drawer-in_200ms_ease-out] flex-col overscroll-contain bg-white pb-[env(safe-area-inset-bottom)] shadow-xl"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="메뉴 닫기"
          className="absolute right-2 top-2 inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <Sidebar onNavigate={onNavigate} account />
      </div>
    </div>
  )
}

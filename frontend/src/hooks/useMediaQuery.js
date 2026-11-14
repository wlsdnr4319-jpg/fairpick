import { useCallback, useSyncExternalStore } from 'react'

// CSS 미디어 쿼리가 맞는지 (화면 폭이 바뀌면 다시 그린다).
// 휴대폰과 넓은 화면의 구조 자체가 다를 때 쓴다 (예: 캘린더). 글자 크기·열 수 정도는 Tailwind 의 sm: 으로 충분하다.
// matchMedia 가 없는 환경(jsdom 테스트 등)은 fallback 값을 쓴다
export function useMediaQuery(query, fallback = false) {
  const subscribe = useCallback(
    (onChange) => {
      if (typeof window === 'undefined' || !window.matchMedia) return () => {}
      const mql = window.matchMedia(query)
      mql.addEventListener('change', onChange)
      return () => mql.removeEventListener('change', onChange)
    },
    [query],
  )
  const get = () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : fallback)
  return useSyncExternalStore(subscribe, get, () => fallback)
}

// Tailwind 의 sm(640px) 과 같은 기준. 이보다 좁으면 휴대폰 화면
export const useIsPhone = () => useMediaQuery('(max-width: 639.98px)', false)

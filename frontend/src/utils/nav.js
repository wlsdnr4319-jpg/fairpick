// 로그인 후 원래 페이지로 돌아간다. 외부 주소로는 보내지 않는다 (오픈 리다이렉트 방지)
export function safeNext(next) {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

// 지금 주소와 가장 잘 맞는 메뉴 하나만 '현재 페이지'로 표시한다.
// /fairs?period=this_weekend 에서는 '박람회 찾기'가 아니라 '이번 주말'이 켜지고, 다른 필터를 더 붙여도 유지된다.
export function activeLink(links, { pathname, search }) {
  const current = new URLSearchParams(search)
  let best = null
  let bestScore = -1
  for (const to of links) {
    const url = new URL(to, 'http://x')
    if (url.pathname !== pathname) continue
    const wanted = [...url.searchParams]
    if (!wanted.every(([k, v]) => current.get(k) === v)) continue
    if (wanted.length > bestScore) {
      best = to
      bestScore = wanted.length
    }
  }
  return best
}

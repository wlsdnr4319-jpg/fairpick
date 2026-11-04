// 로그인 후 원래 페이지로 돌아간다. 외부 주소로는 보내지 않는다 (오픈 리다이렉트 방지)
export function safeNext(next) {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

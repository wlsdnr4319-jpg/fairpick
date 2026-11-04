// 액세스 토큰은 메모리(JS 변수)에만 둔다. 새로고침하면 사라지므로 앱 시작 때 /auth/refresh 로 복구한다.
// 리프레시 토큰은 httpOnly 쿠키라 스크립트로 꺼낼 수 없다 (레퍼런스 10장 토큰 설계).
let accessToken = null
const listeners = new Set()

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
  listeners.forEach((fn) => fn(token))
}

export function onAccessTokenChange(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

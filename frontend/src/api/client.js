import axios from 'axios'

// 모든 API 는 /api/v1 로 시작한다 (레퍼런스 7장).
// withCredentials: 리프레시 토큰을 httpOnly 쿠키로 주고받기 위해 켠다 (4주차).
// 토큰 자동 재발급 인터셉터는 4주차(회원)에 추가한다 (레퍼런스 11장).
export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
})

// 서버 에러는 { error: { code, message } } 형태다. 화면에는 message 를 그대로 보여준다.
export function errorMessage(error, fallback = '잠시 후 다시 시도해 주세요') {
  return error?.response?.data?.error?.message ?? fallback
}

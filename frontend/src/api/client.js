import axios from 'axios'
import { getAccessToken, setAccessToken } from '../store/auth'

// 모든 API 는 /api/v1 로 시작한다 (레퍼런스 7장).
// withCredentials: 리프레시 토큰 쿠키를 주고받기 위해 켠다.
export const api = axios.create({ baseURL: '/api/v1', withCredentials: true })

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 리프레시 토큰은 쓸 때마다 바뀐다(회전). 같은 토큰으로 두 번 요청하면 서버가 탈취로 보고 전부 폐기하므로,
// 동시에 여러 요청이 만료돼도 재발급은 한 번만 보낸다.
let refreshing = null

export function refreshAccessToken() {
  refreshing ??= api
    .post('/auth/refresh')
    .then(({ data }) => {
      setAccessToken(data.access_token)
      return data
    })
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const code = error.response?.data?.error?.code
    if (code === 'TOKEN_EXPIRED' && !original._retry && !original.url.endsWith('/auth/refresh')) {
      original._retry = true
      try {
        await refreshAccessToken()
      } catch {
        setAccessToken(null)
        return Promise.reject(error)
      }
      return api(original)
    }
    return Promise.reject(error)
  },
)

// 서버 에러는 { error: { code, message } } 형태다. 화면에는 message 를 그대로 보여준다.
export function errorMessage(error, fallback = '잠시 후 다시 시도해 주세요') {
  return error?.response?.data?.error?.message ?? fallback
}

export function errorCode(error) {
  return error?.response?.data?.error?.code
}

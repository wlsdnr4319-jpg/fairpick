import { api } from './client'

export async function signup(body) {
  return (await api.post('/auth/signup', body)).data
}

export async function login(body) {
  return (await api.post('/auth/login', body)).data
}

export async function logout() {
  await api.post('/auth/logout')
}

export async function withdraw() {
  await api.delete('/me')
}

export async function fetchMyBookmarks(page = 1) {
  return (await api.get('/me/bookmarks', { params: { page } })).data
}

// 키가 설정된 소셜 로그인 제공자 목록. 키가 없으면 빈 배열이라 버튼이 숨겨진다
export async function fetchOAuthProviders() {
  return (await api.get('/auth/oauth/providers')).data.providers
}

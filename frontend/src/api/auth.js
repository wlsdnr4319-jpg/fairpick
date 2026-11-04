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

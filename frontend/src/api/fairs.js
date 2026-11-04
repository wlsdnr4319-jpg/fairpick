import { api } from './client'

// 빈 값은 쿼리에서 뺀다
function clean(params) {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null && v !== false))
}

export async function fetchFairs(params = {}) {
  const { data } = await api.get('/fairs', { params: clean(params) })
  return data
}

export async function fetchFair(fairId) {
  const { data } = await api.get(`/fairs/${fairId}`)
  return data
}

export async function setBookmark(fairId, on) {
  const { data } = on ? await api.put(`/fairs/${fairId}/bookmark`) : await api.delete(`/fairs/${fairId}/bookmark`)
  return data
}

export async function fetchCategories() {
  return (await api.get('/categories')).data
}

export async function fetchTags() {
  return (await api.get('/tags')).data
}

export async function fetchVenues() {
  return (await api.get('/venues')).data
}

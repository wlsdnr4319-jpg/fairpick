import { api } from './client'

export async function fetchAdminFairs(params = {}) {
  const query = Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  return (await api.get('/admin/fairs', { params: query })).data
}

export async function fetchAdminFair(fairId) {
  return (await api.get(`/admin/fairs/${fairId}`)).data
}

export async function createFair(body) {
  return (await api.post('/admin/fairs', body)).data
}

export async function updateFair(fairId, body) {
  return (await api.patch(`/admin/fairs/${fairId}`, body)).data
}

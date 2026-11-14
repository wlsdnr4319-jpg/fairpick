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

// 표지 이미지: 직접 찍었거나 사용 허락을 받은 이미지만 (서버가 검사해 WebP 로 바꾸고 EXIF 를 지운다)
export async function uploadFairImage(fairId, file) {
  const form = new FormData()
  form.append('file', file)
  form.append('rights_confirmed', 'true')
  return (await api.put(`/admin/fairs/${fairId}/image`, form)).data
}

export async function deleteFairImage(fairId) {
  return (await api.delete(`/admin/fairs/${fairId}/image`)).data
}

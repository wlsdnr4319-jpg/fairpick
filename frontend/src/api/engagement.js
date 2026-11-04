import { api } from './client'

export const fetchCalendar = (month) => api.get('/fairs/calendar', { params: { month } }).then((r) => r.data)
export const fetchReviews = (fairId, page = 1) => api.get(`/fairs/${fairId}/reviews`, { params: { page } }).then((r) => r.data)
export const createVisit = (fairId, body) => api.post(`/fairs/${fairId}/visits`, body).then((r) => r.data)
export const updateVisit = (visitId, body) => api.patch(`/visits/${visitId}`, body).then((r) => r.data)
export const deleteVisit = (visitId) => api.delete(`/visits/${visitId}`)
export const fetchMyVisits = () => api.get('/me/visits').then((r) => r.data)
export const setLike = (visitId, on) =>
  (on ? api.put(`/visits/${visitId}/like`) : api.delete(`/visits/${visitId}/like`)).then((r) => r.data)
export const fetchTagVotes = (fairId) => api.get(`/fairs/${fairId}/tag-votes`).then((r) => r.data)
export const setTagVote = (fairId, tagId, on) =>
  (on ? api.put(`/fairs/${fairId}/tag-votes/${tagId}`) : api.delete(`/fairs/${fairId}/tag-votes/${tagId}`)).then((r) => r.data)
export const fetchNotificationSettings = () => api.get('/me/notification-settings').then((r) => r.data)
export const saveNotificationSettings = (body) => api.put('/me/notification-settings', body).then((r) => r.data)
export const unsubscribe = (token) => api.post('/notifications/unsubscribe', { token }).then((r) => r.data)
export const requestPasswordReset = (email) => api.post('/auth/password-reset/request', { email }).then((r) => r.data)
export const confirmPasswordReset = (token, newPassword) =>
  api.post('/auth/password-reset/confirm', { token, new_password: newPassword }).then((r) => r.data)

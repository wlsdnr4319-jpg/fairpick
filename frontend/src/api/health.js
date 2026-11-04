import { api } from './client'

export async function fetchHealth() {
  const { data } = await api.get('/health')
  return data
}

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: API_BASE })

export function setApiKey(key) {
  api.defaults.headers.common['X-API-Key'] = key
}

export async function submitApplication(data, idempotencyKey) {
  const headers = {}
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
  const res = await api.post('/v1/applications', data, { headers })
  return res.data
}

export async function getApplication(id) {
  const res = await api.get(`/v1/applications/${id}`)
  return res.data
}

export async function listApplications() {
  const res = await api.get('/v1/applications')
  return res.data
}

export async function getHealth() {
  const res = await api.get('/v1/health')
  return res.data
}

export default api

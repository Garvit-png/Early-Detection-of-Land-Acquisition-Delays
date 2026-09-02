import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Attach token to every request
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// On 401, clear token and redirect to login
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

export const getMe = () => api.get('/auth/me')

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const getDashboardStats = () => api.get('/dashboard/stats')

// ─── Projects ─────────────────────────────────────────────────────────────────
export const getProjects = (params) => api.get('/projects', { params })
export const getProject  = (id)     => api.get(`/projects/${id}`)
export const getMapData  = (params) => api.get('/projects/map', { params })

// ─── Predictions ──────────────────────────────────────────────────────────────
export const scoreProject       = (id) => api.post(`/predictions/${id}`)
export const batchScore         = ()   => api.post('/predictions/batch/score-all')
export const getFeatureImportance = () => api.get('/predictions/feature-importance/global')

// ─── Alerts ───────────────────────────────────────────────────────────────────
export const getAlerts        = (params)     => api.get('/alerts', { params })
export const getUnreadCount   = ()           => api.get('/alerts/unread-count')
export const updateAlert      = (id, data)   => api.patch(`/alerts/${id}`, data)
export const deleteAlert      = (id)         => api.delete(`/alerts/${id}`)

// ─── Audit ────────────────────────────────────────────────────────────────────
export const getAuditLogs = (params) => api.get('/audit', { params })

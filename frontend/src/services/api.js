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
export const getStateAnalytics = () => api.get('/dashboard/state-analytics')

// ─── Projects ─────────────────────────────────────────────────────────────────
export const getProjects    = (params) => api.get('/projects', { params })
export const getProject     = (id)     => api.get(`/projects/${id}`)
export const getMapData     = (params) => api.get('/projects/map', { params })
export const createProject  = (data)   => api.post('/projects', data)

// ─── Predictions ──────────────────────────────────────────────────────────────
export const scoreProject       = (id) => api.post(`/predictions/${id}`)
export const batchScore         = ()   => api.post('/predictions/batch/score-all')
export const getFeatureImportance = () => api.get('/predictions/feature-importance/global')
export const getModelStatus     = ()   => api.get('/predictions/model/status')
export const retrainModel       = ()   => api.post('/predictions/model/retrain')

// ─── Alerts ───────────────────────────────────────────────────────────────────
export const getAlerts        = (params)     => api.get('/alerts', { params })
export const getUnreadCount   = ()           => api.get('/alerts/unread-count')
export const updateAlert      = (id, data)   => api.patch(`/alerts/${id}`, data)
export const deleteAlert      = (id)         => api.delete(`/alerts/${id}`)

// ─── Audit ────────────────────────────────────────────────────────────────────
export const getAuditLogs = (params) => api.get('/audit', { params })

// ─── Project Update ───────────────────────────────────────────────────────────
export const updateProject  = (id, data) => api.put(`/projects/${id}`, data)

// ─── Risk History + Similar ───────────────────────────────────────────────────
export const getRiskHistory     = (id, limit = 50) => api.get(`/history/${id}?limit=${limit}`)
export const getSimilarProjects = (id, n = 5)      => api.get(`/history/${id}/similar?top_n=${n}`)

// ─── Actions ──────────────────────────────────────────────────────────────────
export const getActions        = (params)          => api.get('/actions', { params })
export const getProjectActions = (projectId)       => api.get(`/actions/project/${projectId}`)
export const createAction      = (projectId, data) => api.post(`/actions/project/${projectId}`, data)
export const assignAction      = (id, userId)      => api.patch(`/actions/${id}/assign?assigned_to=${userId}`, {})
export const updateAction      = (id, data)        => api.patch(`/actions/${id}`, data)
export const getActionCounts   = ()                => api.get('/actions/counts/summary')

// ─── AI Explanation (OpenAI + RAG) ────────────────────────────────────────────
export const getExplanation = (projectId) => api.post(`/explain/${projectId}`)

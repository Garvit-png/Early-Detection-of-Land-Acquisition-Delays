import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAlerts, updateAlert } from '../services/api'

export default function AlertsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('unresolved') // 'all' | 'unresolved' | 'resolved'
  const [page, setPage] = useState(1)

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 20 }
      if (filter === 'unresolved') params.is_resolved = false
      if (filter === 'resolved')   params.is_resolved = true
      const r = await getAlerts(params)
      setData(r.data)
    } finally {
      setLoading(false)
    }
  }, [page, filter])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])
  useEffect(() => { setPage(1) }, [filter])

  async function markRead(e, alertId) {
    e.stopPropagation()
    await updateAlert(alertId, { is_read: true })
    fetchAlerts()
  }

  async function markResolved(e, alertId) {
    e.stopPropagation()
    await updateAlert(alertId, { is_resolved: true, is_read: true })
    fetchAlerts()
  }

  const timeSince = (dateStr) => {
    const diff = Date.now() - new Date(dateStr).getTime()
    const h = Math.floor(diff / 3600000)
    const d = Math.floor(h / 24)
    if (d > 0) return `${d}d ago`
    if (h > 0) return `${h}h ago`
    return 'just now'
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>
          Alerts {data ? <span style={{ fontSize: 14, fontWeight: 400, color: 'var(--gray-500)' }}>({data.total})</span> : ''}
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {['unresolved', 'all', 'resolved'].map(f => (
            <button key={f}
              className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilter(f)}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading
        ? <div className="spinner" />
        : !data?.items?.length
          ? (
            <div className="empty-state">
              <div style={{ fontSize: 40 }}>🔔</div>
              <div style={{ marginTop: 12 }}>No alerts found.</div>
            </div>
          )
          : (
            <>
              {data.items.map(alert => (
                <div
                  key={alert.id}
                  className={`alert-item ${!alert.is_read ? 'unread' : ''} ${alert.is_resolved ? 'resolved' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/projects/${alert.project_name ? alert.project_name.split(':')[0] : ''}`)}>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div className="alert-title">
                        {!alert.is_read && <span style={{ color: 'var(--danger)', marginRight: 6 }}>●</span>}
                        {alert.title}
                      </div>
                      <div className="alert-meta">
                        📍 {alert.district}, {alert.state} &nbsp;·&nbsp;
                        🕐 {timeSince(alert.created_at)} &nbsp;·&nbsp;
                        <span className={`badge badge-${alert.risk_category}`}>{alert.risk_category} Risk</span>
                        {alert.risk_score && <span style={{ marginLeft: 6 }}>Score: {alert.risk_score}</span>}
                      </div>
                      <div className="alert-msg">{alert.message}</div>
                    </div>

                    <div style={{ display: 'flex', gap: 8, flexShrink: 0, marginLeft: 16 }}>
                      {!alert.is_read && (
                        <button className="btn btn-outline btn-sm" onClick={e => markRead(e, alert.id)}>
                          Mark Read
                        </button>
                      )}
                      {!alert.is_resolved && (
                        <button className="btn btn-primary btn-sm" onClick={e => markResolved(e, alert.id)}>
                          ✓ Resolve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              <div className="pagination">
                <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>Page {page} of {data.total_pages}</span>
                <button className="page-btn" disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Next →</button>
              </div>
            </>
          )
      }
    </>
  )
}

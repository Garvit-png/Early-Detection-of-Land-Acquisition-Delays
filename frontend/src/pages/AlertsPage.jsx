import { useEffect, useState, useCallback } from 'react'
import { getAlerts, updateAlert } from '../services/api'
import { Icon } from '../components/shared/Icons'

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  const hrs  = Math.floor(mins / 60)
  const days = Math.floor(hrs / 24)
  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`
  if (hrs  > 0) return `${hrs} hour${hrs > 1 ? 's' : ''} ago`
  if (mins > 0) return `${mins} minute${mins > 1 ? 's' : ''} ago`
  return 'Just now'
}

export default function AlertsPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('active')   // 'active' | 'resolved' | 'all'
  const [page, setPage] = useState(1)

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 20 }
      if (filter === 'active')   params.is_resolved = false
      if (filter === 'resolved') params.is_resolved = true
      const r = await getAlerts(params)
      setData(r.data)
    } finally {
      setLoading(false)
    }
  }, [page, filter])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])
  useEffect(() => { setPage(1) }, [filter])

  async function markRead(e, id) {
    e.stopPropagation()
    await updateAlert(id, { is_read: true })
    fetchAlerts()
  }
  async function resolve(e, id) {
    e.stopPropagation()
    await updateAlert(id, { is_resolved: true, is_read: true })
    fetchAlerts()
  }

  const FILTER_TABS = [
    { key: 'active',   label: 'Active' },
    { key: 'resolved', label: 'Resolved' },
    { key: 'all',      label: 'All' },
  ]

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Alerts</h1>
          {data && (
            <div className="page-subtitle">
              {data.total.toLocaleString()} alert{data.total !== 1 ? 's' : ''} {filter !== 'all' ? `(${filter})` : ''}
            </div>
          )}
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 4, background: 'var(--gray-100)', padding: 4, borderRadius: 'var(--radius)' }}>
          {FILTER_TABS.map(({ key, label }) => (
            <button
              key={key}
              className="btn btn-sm"
              style={{
                background: filter === key ? '#fff' : 'transparent',
                color: filter === key ? 'var(--gray-800)' : 'var(--gray-500)',
                boxShadow: filter === key ? 'var(--shadow-xs)' : 'none',
                border: 'none',
              }}
              onClick={() => setFilter(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading
        ? <div className="spinner-wrap"><div className="spinner" /></div>
        : !data?.items?.length
          ? (
            <div className="empty-state">
              <div className="empty-state-icon"><Icon.Bell /></div>
              <div className="empty-state-text">No alerts found</div>
              <div className="empty-state-sub">
                {filter === 'active' ? 'No active alerts at this time.' : 'No alerts match the current filter.'}
              </div>
            </div>
          )
          : (
            <>
              {data.items.map(alert => (
                <div
                  key={alert.id}
                  className={`alert-card ${!alert.is_read ? 'unread' : ''} ${alert.is_resolved ? 'resolved' : ''}`}>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="alert-card-title">
                        {!alert.is_read && (
                          <span style={{
                            width: 7, height: 7, borderRadius: '50%',
                            background: 'var(--danger)', display: 'inline-block', flexShrink: 0
                          }} />
                        )}
                        {alert.title}
                      </div>

                      <div className="alert-card-meta">
                        <span>{alert.district}, {alert.state}</span>
                        <span style={{ color: 'var(--gray-300)' }}>|</span>
                        <span>{timeAgo(alert.created_at)}</span>
                        <span style={{ color: 'var(--gray-300)' }}>|</span>
                        <span className={`risk-badge ${alert.risk_category}`} style={{ fontSize: 10, padding: '1px 7px' }}>
                          <span className={`risk-dot ${alert.risk_category}`} />
                          {alert.risk_category} Risk
                        </span>
                        {alert.risk_score && (
                          <span style={{ color: 'var(--gray-500)' }}>Score: {alert.risk_score}</span>
                        )}
                        {alert.is_resolved && (
                          <span style={{ color: 'var(--success)', fontSize: 11, fontWeight: 600 }}>Resolved</span>
                        )}
                      </div>

                      <div className="alert-card-msg">{alert.message}</div>
                    </div>

                    {!alert.is_resolved && (
                      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                        {!alert.is_read && (
                          <button className="btn btn-outline btn-sm" onClick={e => markRead(e, alert.id)}>
                            Mark Read
                          </button>
                        )}
                        <button className="btn btn-primary btn-sm" onClick={e => resolve(e, alert.id)}>
                          <Icon.Check />
                          Resolve
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {data.total_pages > 1 && (
                <div className="pagination" style={{ background: 'var(--white)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-lg)', padding: '12px 20px', boxShadow: 'var(--shadow-sm)' }}>
                  <span className="pagination-info">
                    Page {page} of {data.total_pages}
                  </span>
                  <div className="pagination-btns">
                    <button className="pager-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
                    <button className="pager-btn" disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Next</button>
                  </div>
                </div>
              )}
            </>
          )
      }
    </>
  )
}

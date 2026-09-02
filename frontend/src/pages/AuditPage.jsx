import { useEffect, useState } from 'react'
import { getAuditLogs } from '../services/api'
import { useAuth } from '../store/authStore'
import { Navigate } from 'react-router-dom'

export default function AuditPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  if (user?.role !== 'central') return <Navigate to="/dashboard" replace />

  useEffect(() => {
    setLoading(true)
    getAuditLogs({ page, page_size: 50 })
      .then(r => setData(r.data))
      .finally(() => setLoading(false))
  }, [page])

  const ACTION_COLORS = {
    LOGIN: '#16a34a', LOGOUT: '#64748b',
    VIEW_PROJECT: '#3b82f6', LIST_PROJECTS: '#6366f1',
    SCORE_PROJECT: '#d97706', BATCH_SCORE: '#ea580c',
    UPDATE_ALERT: '#8b5cf6', IMPORT_CSV: '#0891b2',
  }

  return (
    <>
      <h1 className="page-title">Audit Logs</h1>

      {loading
        ? <div className="spinner" />
        : (
          <div className="card" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th><th>Time</th><th>User</th><th>Action</th>
                    <th>Resource</th><th>Detail</th><th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items?.map(log => (
                    <tr key={log.id}>
                      <td style={{ color: 'var(--gray-400)', fontSize: 11 }}>{log.id}</td>
                      <td style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td style={{ fontWeight: 500 }}>{log.username}</td>
                      <td>
                        <span style={{
                          background: ACTION_COLORS[log.action] || '#94a3b8',
                          color: '#fff', padding: '2px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600
                        }}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ fontSize: 12 }}>{log.resource}{log.resource_id ? ` #${log.resource_id}` : ''}</td>
                      <td style={{ fontSize: 11, color: 'var(--gray-600)', maxWidth: 300,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.detail}
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--gray-400)' }}>{log.ip_address}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination" style={{ padding: '12px 20px' }}>
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                Page {page} of {data?.total_pages}
              </span>
              <button className="page-btn" disabled={page >= data?.total_pages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </div>
        )
      }
    </>
  )
}

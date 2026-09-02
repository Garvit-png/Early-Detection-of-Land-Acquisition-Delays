import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { getAuditLogs } from '../services/api'
import { useAuth } from '../store/authStore'

const ACTION_STYLES = {
  LOGIN:        { background: '#d1fae5', color: '#065f46' },
  VIEW_PROJECT: { background: '#dbeafe', color: '#1e3a8a' },
  LIST_PROJECTS:{ background: '#ede9fe', color: '#3730a3' },
  SCORE_PROJECT:{ background: '#fef3c7', color: '#78350f' },
  BATCH_SCORE:  { background: '#ffedd5', color: '#7c2d12' },
  UPDATE_ALERT: { background: '#fce7f3', color: '#831843' },
  IMPORT_CSV:   { background: '#cffafe', color: '#164e63' },
}

export default function AuditPage() {
  const { user } = useAuth()
  if (user?.role !== 'central') return <Navigate to="/dashboard" replace />

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  useEffect(() => {
    setLoading(true)
    getAuditLogs({ page, page_size: 50 })
      .then(r => setData(r.data))
      .finally(() => setLoading(false))
  }, [page])

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Logs</h1>
          <div className="page-subtitle">
            Full record of all user actions in the system. Visible to Central users only.
          </div>
        </div>
      </div>

      {loading
        ? <div className="spinner-wrap"><div className="spinner" /></div>
        : (
          <div className="table-container">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Detail</th>
                    <th>IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items?.map(log => {
                    const style = ACTION_STYLES[log.action] || { background: 'var(--gray-100)', color: 'var(--gray-600)' }
                    return (
                      <tr key={log.id} style={{ cursor: 'default' }}>
                        <td style={{ color: 'var(--gray-400)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                          {log.id}
                        </td>
                        <td style={{ fontSize: 11, color: 'var(--gray-500)', whiteSpace: 'nowrap' }}>
                          {new Date(log.created_at).toLocaleString('en-IN', {
                            day: '2-digit', month: 'short', year: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                          })}
                        </td>
                        <td style={{ fontWeight: 600, fontSize: 13 }}>{log.username}</td>
                        <td>
                          <span className="action-tag" style={style}>
                            {log.action}
                          </span>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--gray-600)' }}>
                          {log.resource}
                          {log.resource_id ? <span style={{ color: 'var(--gray-400)' }}> #{log.resource_id}</span> : ''}
                        </td>
                        <td style={{
                          fontSize: 11, color: 'var(--gray-500)',
                          maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                        }}>
                          {log.detail}
                        </td>
                        <td style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--gray-400)' }}>
                          {log.ip_address}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <span className="pagination-info">
                Page {page} of {data?.total_pages ?? 1}
              </span>
              <div className="pagination-btns">
                <button className="pager-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
                <button className="pager-btn" disabled={page >= (data?.total_pages ?? 1)} onClick={() => setPage(p => p + 1)}>Next</button>
              </div>
            </div>
          </div>
        )
      }
    </>
  )
}

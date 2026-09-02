import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getActions, updateAction, getActionCounts } from '../services/api'
import { Icon } from '../components/shared/Icons'

const STATUS_COLOR = {
  open:         'var(--warning)',
  in_progress:  'var(--primary)',
  completed:    'var(--success)',
  overridden:   'var(--gray-400)',
}
const PRIORITY_COLOR = {
  critical: '#7c0000',
  high:     'var(--danger)',
  medium:   'var(--warning)',
  low:      'var(--success)',
}

function timeAgo(ds) {
  if (!ds) return '—'
  const d = Math.floor((Date.now() - new Date(ds)) / 86400000)
  return d === 0 ? 'Today' : d === 1 ? 'Yesterday' : `${d}d ago`
}

function StatusBadge({ status }) {
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:4,
      padding:'2px 8px', borderRadius:3, fontSize:11, fontWeight:600,
      color: STATUS_COLOR[status] || 'var(--gray-500)',
      background: `${STATUS_COLOR[status]}18` || 'var(--gray-100)',
      border: `1px solid ${STATUS_COLOR[status]}40`,
    }}>
      <span style={{ width:6, height:6, borderRadius:'50%', background: STATUS_COLOR[status], display:'inline-block' }} />
      {status.replace('_', ' ')}
    </span>
  )
}

export default function ActionTrackingPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data,   setData]   = useState(null)
  const [counts, setCounts] = useState({ open:0, in_progress:0, completed:0, overridden:0, my_open:0 })
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(null)
  const [completeNote, setCompleteNote] = useState('')
  const [showNoteFor, setShowNoteFor] = useState(null)

  const statusFilter  = searchParams.get('status')  || ''
  const priorityFilter = searchParams.get('priority') || ''
  const mineOnly      = searchParams.get('mine') === '1'
  const page          = parseInt(searchParams.get('page') || '1')

  const load = useCallback(() => {
    setLoading(true)
    const params = { page, page_size: 20 }
    if (statusFilter)   params.status   = statusFilter
    if (priorityFilter) params.priority = priorityFilter
    if (mineOnly)       params.assigned_to_me = true
    Promise.all([
      getActions(params),
      getActionCounts(),
    ]).then(([r, c]) => {
      setData(r.data)
      setCounts(c.data)
    }).finally(() => setLoading(false))
  }, [searchParams])

  useEffect(() => { load() }, [load])

  function setParam(k, v) {
    const p = new URLSearchParams(searchParams)
    if (v) p.set(k, v); else p.delete(k)
    p.set('page', '1')
    setSearchParams(p)
  }

  async function handleComplete(id) {
    setCompleting(id)
    try {
      await updateAction(id, { status: 'completed', completion_note: completeNote || undefined })
      setShowNoteFor(null)
      setCompleteNote('')
      load()
    } catch(e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally { setCompleting(null) }
  }

  async function handleStart(id) {
    await updateAction(id, { status: 'in_progress' })
    load()
  }

  const KPI = ({ label, value, color, filter }) => (
    <div className="kpi-card" style={{ cursor:'pointer', borderBottom:`3px solid ${color}` }}
      onClick={() => setParam('status', filter)}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color }}>{value}</div>
    </div>
  )

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Action Tracking</h1>
          <div className="page-subtitle">Officer review outcomes · assigned tasks · completion status</div>
        </div>
        <button className="btn btn-outline btn-sm" onClick={() => setSearchParams(new URLSearchParams())}>
          <Icon.X /> Clear Filters
        </button>
      </div>

      {/* KPI strip */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <KPI label="Open"        value={counts.open}        color="var(--warning)" filter="open" />
        <KPI label="In Progress" value={counts.in_progress} color="var(--primary)" filter="in_progress" />
        <KPI label="Completed"   value={counts.completed}   color="var(--success)" filter="completed" />
        <KPI label="Overridden"  value={counts.overridden}  color="var(--gray-400)" filter="overridden" />
        <div className="kpi-card" style={{ cursor:'pointer', borderBottom:'3px solid var(--primary)' }}
          onClick={() => setParam('mine', mineOnly ? '' : '1')}>
          <div className="kpi-label">Assigned to Me</div>
          <div className="kpi-value" style={{ color:'var(--primary)' }}>{counts.my_open}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="card" style={{ padding:'12px 20px', marginBottom:20 }}>
        <div style={{ display:'flex', gap:12, flexWrap:'wrap', alignItems:'flex-end' }}>
          <div>
            <label className="field-label">Status</label>
            <select className="field-input" style={{ width:130 }} value={statusFilter}
              onChange={e => setParam('status', e.target.value)}>
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="overridden">Overridden</option>
            </select>
          </div>
          <div>
            <label className="field-label">Priority</label>
            <select className="field-input" style={{ width:120 }} value={priorityFilter}
              onChange={e => setParam('priority', e.target.value)}>
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:1 }}>
            <input type="checkbox" id="mine" checked={mineOnly} onChange={e => setParam('mine', e.target.checked ? '1' : '')} style={{ width:15, height:15 }} />
            <label htmlFor="mine" className="field-label" style={{ cursor:'pointer', margin:0 }}>My Actions Only</label>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        {loading
          ? <div className="spinner-wrap"><div className="spinner" /></div>
          : !data?.items?.length
            ? (
              <div className="empty-state">
                <div className="empty-state-icon"><Icon.Audit /></div>
                <div className="empty-state-text">No actions found</div>
                <div className="empty-state-sub">Create action items from project detail pages</div>
              </div>
            )
            : (
              <>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Action</th>
                        <th>Project</th>
                        <th>Rule</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Decision</th>
                        <th>Assigned</th>
                        <th>Due</th>
                        <th>Created</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map(a => (
                        <tr key={a.id}>
                          <td style={{ color:'var(--gray-400)', fontSize:11, fontFamily:'var(--font-mono)' }}>{a.id}</td>
                          <td>
                            <div style={{ fontWeight:600, fontSize:13, color:'var(--gray-800)', maxWidth:220 }}>
                              {a.title}
                            </div>
                            {a.description && <div style={{ fontSize:11, color:'var(--gray-500)', marginTop:2, maxWidth:220, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{a.description}</div>}
                            {a.completion_note && <div style={{ fontSize:11, color:'var(--success)', marginTop:2 }}>✓ {a.completion_note}</div>}
                          </td>
                          <td>
                            {a.project_id ? (
                              <button className="btn btn-ghost btn-xs" style={{ padding:'2px 6px', textAlign:'left' }}
                                onClick={() => navigate(`/projects/${a.project_id}`)}>
                                <span style={{ fontSize:11, fontFamily:'var(--font-mono)' }}>{a.project_id}</span>
                              </button>
                            ) : '—'}
                            {a.district && <div style={{ fontSize:10, color:'var(--gray-400)' }}>{a.district}, {a.state}</div>}
                          </td>
                          <td>
                            {a.rule_id && (
                              <span style={{ fontSize:10, fontFamily:'var(--font-mono)', fontWeight:700, background:'var(--primary-light)', color:'var(--primary)', padding:'2px 6px', borderRadius:3 }}>
                                {a.rule_id}
                              </span>
                            )}
                          </td>
                          <td>
                            <span style={{ fontSize:11, fontWeight:700, color: PRIORITY_COLOR[a.priority] || 'var(--gray-600)' }}>
                              {a.priority}
                            </span>
                          </td>
                          <td><StatusBadge status={a.status} /></td>
                          <td>
                            <span style={{ fontSize:11, color:'var(--gray-600)', textTransform:'capitalize' }}>
                              {a.officer_decision}
                            </span>
                          </td>
                          <td style={{ fontSize:12 }}>{a.assigned_to_name || <span style={{ color:'var(--gray-400)' }}>Unassigned</span>}</td>
                          <td style={{ fontSize:11, color: a.due_date && new Date(a.due_date) < new Date() && a.status !== 'completed' ? 'var(--danger)' : 'var(--gray-600)' }}>
                            {a.due_date ? new Date(a.due_date).toLocaleDateString('en-IN') : '—'}
                          </td>
                          <td style={{ fontSize:11, color:'var(--gray-400)', whiteSpace:'nowrap' }}>
                            {timeAgo(a.created_at)}
                          </td>
                          <td>
                            {a.status !== 'completed' && a.status !== 'overridden' && (
                              <div style={{ display:'flex', gap:4' }}>
                                {a.status === 'open' && (
                                  <button className="btn btn-ghost btn-xs" title="Start" onClick={() => handleStart(a.id)}>Start</button>
                                )}
                                {showNoteFor === a.id ? (
                                  <div style={{ display:'flex', gap:4, alignItems:'center' }}>
                                    <input className="field-input" style={{ width:140, padding:'3px 8px', fontSize:11 }}
                                      placeholder="Completion note…" value={completeNote}
                                      onChange={e => setCompleteNote(e.target.value)}
                                      onKeyDown={e => e.key==='Enter' && handleComplete(a.id)} autoFocus />
                                    <button className="btn btn-primary btn-xs" disabled={completing===a.id}
                                      onClick={() => handleComplete(a.id)}>
                                      <Icon.Check />
                                    </button>
                                    <button className="btn btn-ghost btn-xs" onClick={() => setShowNoteFor(null)}><Icon.X /></button>
                                  </div>
                                ) : (
                                  <button className="btn btn-outline btn-xs" title="Mark Complete"
                                    onClick={() => { setShowNoteFor(a.id); setCompleteNote('') }}>
                                    Done
                                  </button>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <span className="pagination-info">
                    {data.total} action{data.total !== 1 ? 's' : ''} total
                  </span>
                  <div className="pagination-btns">
                    <button className="pager-btn" disabled={page<=1} onClick={() => setParam('page', page-1)}>Prev</button>
                    <button className="pager-btn" disabled={page>=data.total_pages} onClick={() => setParam('page', page+1)}>Next</button>
                  </div>
                </div>
              </>
            )
        }
      </div>
    </>
  )
}

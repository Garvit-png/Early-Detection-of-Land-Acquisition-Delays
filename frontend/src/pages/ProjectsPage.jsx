import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getProjects, scoreProject, exportCSV } from '../services/api'
import { Icon } from '../components/shared/Icons'

const STAGES = [
  'Section 11 Notification', 'Section 19 Declaration', 'Award Passed',
  'Compensation Disbursed', 'Possession Taken', 'R&R Completed',
]
const TYPES = [
  'National Highway', 'State Highway', 'Railway Line', 'Metro Rail', 'Expressway',
  'Dam / Reservoir', 'Irrigation Canal', 'Industrial Corridor', 'Power Plant',
  'Solar Park', 'Transmission Line', 'Airport Expansion', 'Port Development',
  'Smart City', 'Housing Scheme',
]

function RiskBadge({ cat }) {
  if (!cat) return <span className="risk-badge none">Unscored</span>
  return (
    <span className={`risk-badge ${cat}`}>
      <span className={`risk-dot ${cat}`} />
      {cat}
    </span>
  )
}

function Select({ label, value, onChange, children, style }) {
  return (
    <div style={style}>
      <label className="field-label">{label}</label>
      <select className="field-input" value={value} onChange={onChange}>{children}</select>
    </div>
  )
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scoringId, setScoringId] = useState(null)
  const [exporting, setExporting]  = useState(false)

  async function handleExport() {
    setExporting(true)
    try {
      const params = {}
      if (riskFilter)  params.risk_category = riskFilter
      if (searchParams.get('state')) params.state = searchParams.get('state')
      const r = await exportCSV(params)
      const url  = URL.createObjectURL(new Blob([r.data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href  = url
      link.download = `land_acquisition_MIS_${new Date().toISOString().slice(0,10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch(e) {
      alert('Export failed: ' + e.message)
    } finally { setExporting(false) }
  }

  const page          = parseInt(searchParams.get('page') || '1')
  const riskFilter    = searchParams.get('risk_category') || ''
  const typeFilter    = searchParams.get('project_type') || ''
  const stageFilter   = searchParams.get('current_stage') || ''
  const searchQuery   = searchParams.get('search') || ''

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 25 }
      if (riskFilter)  params.risk_category = riskFilter
      if (typeFilter)  params.project_type  = typeFilter
      if (stageFilter) params.current_stage = stageFilter
      if (searchQuery) params.search        = searchQuery
      const r = await getProjects(params)
      setData(r.data)
    } finally {
      setLoading(false)
    }
  }, [searchParams])

  useEffect(() => { fetchData() }, [fetchData])

  function setParam(key, val) {
    const p = new URLSearchParams(searchParams)
    if (val) p.set(key, val); else p.delete(key)
    p.set('page', '1')
    setSearchParams(p)
  }

  function clearFilters() {
    setSearchParams(new URLSearchParams())
  }

  async function handleScore(e, projectId) {
    e.stopPropagation()
    setScoringId(projectId)
    try {
      await scoreProject(projectId)
      fetchData()
    } catch (err) {
      alert('Scoring error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setScoringId(null)
    }
  }

  const hasFilters = riskFilter || typeFilter || stageFilter || searchQuery

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          {data && <div className="page-subtitle">{data.total.toLocaleString()} projects found</div>}
        </div>
        <div style={{ display:'flex', gap:8 }}>
          <button className="btn btn-outline" onClick={handleExport} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/projects/new')}>
            <Icon.Lightning /> Submit New Project
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="card" style={{ marginBottom: 20, padding: '14px 20px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: '1', minWidth: 180 }}>
            <label className="field-label">
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 12, display: 'flex', flexShrink: 0 }}><Icon.Search /></span>
                Search
              </span>
            </label>
            <input className="field-input" placeholder="Project name, ID or district"
              value={searchQuery}
              onChange={e => setParam('search', e.target.value)} />
          </div>
          <Select label="Risk Level" value={riskFilter} style={{ minWidth: 130 }}
            onChange={e => setParam('risk_category', e.target.value)}>
            <option value="">All</option>
            <option>High</option><option>Medium</option><option>Low</option>
          </Select>
          <Select label="Project Type" value={typeFilter} style={{ minWidth: 160 }}
            onChange={e => setParam('project_type', e.target.value)}>
            <option value="">All Types</option>
            {TYPES.map(t => <option key={t}>{t}</option>)}
          </Select>
          <Select label="Stage" value={stageFilter} style={{ minWidth: 200 }}
            onChange={e => setParam('current_stage', e.target.value)}>
            <option value="">All Stages</option>
            {STAGES.map(s => <option key={s}>{s}</option>)}
          </Select>
          {hasFilters && (
            <button className="btn btn-ghost btn-sm" style={{ marginBottom: 1 }} onClick={clearFilters}>
              <Icon.X /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        {loading
          ? <div className="spinner-wrap"><div className="spinner" /></div>
          : !data?.items?.length
            ? (
              <div className="empty-state">
                <div className="empty-state-icon"><Icon.Projects /></div>
                <div className="empty-state-text">No projects found</div>
                <div className="empty-state-sub">Try adjusting your filters</div>
              </div>
            )
            : (
              <>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Project ID</th>
                        <th>Project Name</th>
                        <th>Type</th>
                        <th>State</th>
                        <th>District</th>
                        <th>Stage</th>
                        <th>Risk Level</th>
                        <th>Risk Score</th>
                        <th>Compensation</th>
                        <th>Legal Dispute</th>
                        <th style={{ width: 48 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map(p => (
                        <tr key={p.id} onClick={() => navigate(`/projects/${p.project_id}`)}>
                          <td>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-500)' }}>
                              {p.project_id}
                            </span>
                          </td>
                          <td style={{ fontWeight: 500, color: 'var(--gray-900)', maxWidth: 180 }}>
                            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {p.project_name}
                            </div>
                          </td>
                          <td style={{ fontSize: 12 }}>{p.project_type}</td>
                          <td>{p.state}</td>
                          <td>{p.district}</td>
                          <td style={{ fontSize: 11, color: 'var(--gray-500)', maxWidth: 160 }}>
                            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {p.current_stage}
                            </div>
                          </td>
                          <td><RiskBadge cat={p.risk_category} /></td>
                          <td>
                            {p.risk_score != null
                              ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <div className="progress-wrap" style={{ width: 56 }}>
                                    <div className={`progress-bar ${
                                      p.risk_category === 'High' ? 'danger' :
                                      p.risk_category === 'Medium' ? 'warning' : 'success'
                                    }`} style={{ width: `${p.risk_score}%` }} />
                                  </div>
                                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--gray-700)' }}>
                                    {p.risk_score}
                                  </span>
                                </div>
                              )
                              : <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>—</span>
                            }
                          </td>
                          <td style={{ fontSize: 12 }}>
                            {p.compensation_pct != null
                              ? <span style={{ color: p.compensation_pct < 50 ? 'var(--danger)' : 'inherit' }}>
                                  {p.compensation_pct}%
                                </span>
                              : '—'
                            }
                          </td>
                          <td>
                            {p.has_legal_dispute
                              ? <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--danger)' }}>Yes</span>
                              : <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>No</span>}
                          </td>
                          <td onClick={e => e.stopPropagation()}>
                            <button
                              className="btn btn-ghost btn-xs"
                              title="Re-score this project"
                              disabled={scoringId === p.project_id}
                              onClick={e => handleScore(e, p.project_id)}
                              style={{ padding: '4px 6px' }}>
                              <Icon.Refresh />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <span className="pagination-info">
                    Showing {(page - 1) * 25 + 1}–{Math.min(page * 25, data.total)} of {data.total.toLocaleString()} projects
                  </span>
                  <div className="pagination-btns">
                    <button className="pager-btn" disabled={page <= 1}
                      onClick={() => setParam('page', page - 1)}>
                      Previous
                    </button>
                    {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
                      const pg = Math.max(1, Math.min(data.total_pages - 4, page - 2)) + i
                      return (
                        <button key={pg} className={`pager-btn ${pg === page ? 'active' : ''}`}
                          onClick={() => setParam('page', pg)}>{pg}</button>
                      )
                    })}
                    <button className="pager-btn" disabled={page >= data.total_pages}
                      onClick={() => setParam('page', page + 1)}>
                      Next
                    </button>
                  </div>
                </div>
              </>
            )
        }
      </div>
    </>
  )
}

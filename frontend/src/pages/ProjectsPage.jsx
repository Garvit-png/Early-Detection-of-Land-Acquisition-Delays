import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getProjects, scoreProject } from '../services/api'
import { useAuth } from '../store/authStore'

const STAGES = [
  'Section 11 Notification', 'Section 19 Declaration', 'Award Passed',
  'Compensation Disbursed', 'Possession Taken', 'R&R Completed'
]
const TYPES = [
  'National Highway', 'State Highway', 'Railway Line', 'Metro Rail', 'Expressway',
  'Dam / Reservoir', 'Irrigation Canal', 'Industrial Corridor', 'Power Plant',
  'Solar Park', 'Transmission Line', 'Airport Expansion', 'Port Development',
  'Smart City', 'Housing Scheme'
]

function RiskBadge({ cat }) {
  if (!cat) return <span className="badge badge-none">—</span>
  return <span className={`badge badge-${cat}`}>{cat}</span>
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scoringId, setScoringId] = useState(null)

  const filters = {
    risk_category: searchParams.get('risk_category') || '',
    project_type:  searchParams.get('project_type') || '',
    current_stage: searchParams.get('current_stage') || '',
    search:        searchParams.get('search') || '',
    page: parseInt(searchParams.get('page') || '1'),
  }

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page: filters.page, page_size: 20 }
      if (filters.risk_category) params.risk_category = filters.risk_category
      if (filters.project_type)  params.project_type  = filters.project_type
      if (filters.current_stage) params.current_stage = filters.current_stage
      if (filters.search)        params.search        = filters.search
      const r = await getProjects(params)
      setData(r.data)
    } finally {
      setLoading(false)
    }
  }, [searchParams])

  useEffect(() => { fetchData() }, [fetchData])

  function setFilter(key, val) {
    const p = new URLSearchParams(searchParams)
    if (val) p.set(key, val); else p.delete(key)
    p.set('page', '1')
    setSearchParams(p)
  }

  function setPage(n) {
    const p = new URLSearchParams(searchParams)
    p.set('page', n)
    setSearchParams(p)
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

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>
          Projects {data ? <span style={{ fontSize: 14, fontWeight: 400, color: 'var(--gray-500)' }}>({data.total.toLocaleString()} total)</span> : ''}
        </h1>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20, padding: '14px 20px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label className="form-label">Search</label>
            <input className="form-input" style={{ width: 200 }} placeholder="Name / ID / District"
              value={filters.search}
              onChange={e => setFilter('search', e.target.value)} />
          </div>
          <div>
            <label className="form-label">Risk</label>
            <select className="form-input form-select" style={{ width: 130 }}
              value={filters.risk_category}
              onChange={e => setFilter('risk_category', e.target.value)}>
              <option value="">All</option>
              <option>High</option><option>Medium</option><option>Low</option>
            </select>
          </div>
          <div>
            <label className="form-label">Type</label>
            <select className="form-input form-select" style={{ width: 160 }}
              value={filters.project_type}
              onChange={e => setFilter('project_type', e.target.value)}>
              <option value="">All Types</option>
              {TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="form-label">Stage</label>
            <select className="form-input form-select" style={{ width: 200 }}
              value={filters.current_stage}
              onChange={e => setFilter('current_stage', e.target.value)}>
              <option value="">All Stages</option>
              {STAGES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <button className="btn btn-outline btn-sm" onClick={() => setSearchParams(new URLSearchParams())}>
            Clear
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0 }}>
        {loading
          ? <div className="spinner" />
          : !data?.items?.length
            ? <div className="empty-state">No projects found.</div>
            : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Project ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>State</th>
                        <th>District</th>
                        <th>Stage</th>
                        <th>Risk</th>
                        <th>Risk Score</th>
                        <th>Compensation</th>
                        <th>Legal</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map(p => (
                        <tr key={p.id} style={{ cursor: 'pointer' }}
                          onClick={() => navigate(`/projects/${p.project_id}`)}>
                          <td><code style={{ fontSize: 11 }}>{p.project_id}</code></td>
                          <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {p.project_name}
                          </td>
                          <td style={{ fontSize: 12 }}>{p.project_type}</td>
                          <td>{p.state}</td>
                          <td>{p.district}</td>
                          <td style={{ fontSize: 11, maxWidth: 140, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {p.current_stage}
                          </td>
                          <td><RiskBadge cat={p.risk_category} /></td>
                          <td>
                            {p.risk_score != null ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div className="risk-bar-wrap" style={{ width: 50 }}>
                                  <div className={`risk-bar ${p.risk_category}`} style={{ width: `${p.risk_score}%` }} />
                                </div>
                                <span style={{ fontSize: 12, fontWeight: 600 }}>{p.risk_score}</span>
                              </div>
                            ) : <span style={{ color: 'var(--gray-400)', fontSize: 11 }}>unscored</span>}
                          </td>
                          <td style={{ fontSize: 12 }}>
                            {p.compensation_pct != null ? `${p.compensation_pct}%` : '—'}
                          </td>
                          <td>
                            {p.has_legal_dispute
                              ? <span style={{ color: 'var(--danger)', fontSize: 12 }}>⚠ Yes</span>
                              : <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>No</span>}
                          </td>
                          <td>
                            <button className="btn btn-outline btn-sm"
                              disabled={scoringId === p.project_id}
                              onClick={e => handleScore(e, p.project_id)}>
                              {scoringId === p.project_id ? '…' : '⚡'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="pagination" style={{ padding: '12px 20px' }}>
                  <button className="page-btn" disabled={filters.page <= 1} onClick={() => setPage(filters.page - 1)}>← Prev</button>
                  <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                    Page {filters.page} of {data.total_pages}
                  </span>
                  <button className="page-btn" disabled={filters.page >= data.total_pages} onClick={() => setPage(filters.page + 1)}>Next →</button>
                </div>
              </>
            )
        }
      </div>
    </>
  )
}

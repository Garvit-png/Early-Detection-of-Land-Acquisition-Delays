import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { getDashboardStats, batchScore } from '../services/api'
import { useAuth } from '../store/authStore'

const COLORS = { High: '#dc2626', Medium: '#d97706', Low: '#16a34a' }
const PIE_COLORS = ['#dc2626', '#d97706', '#16a34a', '#94a3b8']

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scoring, setScoring] = useState(false)

  useEffect(() => {
    getDashboardStats()
      .then(r => setStats(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function handleBatchScore() {
    setScoring(true)
    try {
      const r = await batchScore()
      alert(`Scored ${r.data.scored} projects!`)
      const r2 = await getDashboardStats()
      setStats(r2.data)
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally {
      setScoring(false)
    }
  }

  if (loading) return <div className="spinner" />
  if (!stats) return <div className="empty-state">Failed to load stats.</div>

  const pieData = [
    { name: 'High Risk',   value: stats.high_risk },
    { name: 'Medium Risk', value: stats.medium_risk },
    { name: 'Low Risk',    value: stats.low_risk },
    { name: 'Unscored',   value: stats.unscored },
  ]

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Dashboard Overview</h1>
        {(user?.role === 'central' || user?.role === 'state') && (
          <button className="btn btn-primary" onClick={handleBatchScore} disabled={scoring}>
            {scoring ? 'Scoring…' : '⚡ Batch Score Projects'}
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Total Projects</div>
          <div className="stat-value">{stats.total_projects.toLocaleString()}</div>
        </div>
        <div className="stat-card danger">
          <div className="stat-label">High Risk</div>
          <div className="stat-value">{stats.high_risk.toLocaleString()}</div>
          <div className="stat-sub">Immediate attention needed</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-label">Medium Risk</div>
          <div className="stat-value">{stats.medium_risk.toLocaleString()}</div>
        </div>
        <div className="stat-card success">
          <div className="stat-label">Low Risk</div>
          <div className="stat-value">{stats.low_risk.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Risk Score</div>
          <div className="stat-value">{stats.avg_risk_score}</div>
          <div className="stat-sub">out of 100</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-label">Legal Disputes</div>
          <div className="stat-value">{stats.projects_with_legal_dispute.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Compensation</div>
          <div className="stat-value">{stats.avg_compensation_pct}%</div>
          <div className="stat-sub">disbursed</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg R&R</div>
          <div className="stat-value">{stats.avg_rr_completion_pct}%</div>
          <div className="stat-sub">completed</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {/* Risk Distribution Pie */}
        <div className="card">
          <div className="card-title">Risk Distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top States by High Risk */}
        <div className="card">
          <div className="card-title">High Risk by State (Top 8)</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stats.by_state.slice(0, 8)} layout="vertical" margin={{ left: 80 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={80} />
              <Tooltip />
              <Bar dataKey="high" fill="#dc2626" name="High Risk" radius={[0, 3, 3, 0]} />
              <Bar dataKey="medium" fill="#d97706" name="Medium Risk" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {/* Avg Risk by Project Type */}
        <div className="card">
          <div className="card-title">Avg Risk Score by Project Type</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stats.by_project_type} layout="vertical" margin={{ left: 100 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="project_type" tick={{ fontSize: 10 }} width={100} />
              <Tooltip />
              <Bar dataKey="avg_risk" name="Avg Risk Score" radius={[0, 3, 3, 0]}
                fill="#3b82f6"
                label={{ position: 'right', fontSize: 10 }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Projects by Stage */}
        <div className="card">
          <div className="card-title">Projects by Acquisition Stage</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stats.by_stage} margin={{ left: 10 }}>
              <XAxis dataKey="stage" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent High Risk Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div className="card-title" style={{ margin: 0 }}>Top High-Risk Projects</div>
          <button className="btn btn-outline btn-sm" onClick={() => navigate('/projects?risk_category=High')}>
            View All →
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project ID</th><th>Name</th><th>State</th><th>District</th><th>Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_high_risk.map(p => (
                <tr key={p.project_id} style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/projects/${p.project_id}`)}>
                  <td><code style={{ fontSize: 12 }}>{p.project_id}</code></td>
                  <td>{p.project_name}</td>
                  <td>{p.state}</td>
                  <td>{p.district}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="risk-bar-wrap" style={{ width: 60 }}>
                        <div className="risk-bar High" style={{ width: `${p.risk_score}%` }} />
                      </div>
                      <span style={{ fontWeight: 600, color: 'var(--danger)' }}>{p.risk_score}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

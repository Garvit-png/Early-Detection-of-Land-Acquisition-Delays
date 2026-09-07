import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { getDashboardStats, batchScore } from '../services/api'
import { useAuth } from '../store/authStore'
import { Icon } from '../components/shared/Icons'
import ModelStatusCard from '../components/dashboard/ModelStatusCard'

const RISK_COLORS = {
  'High Risk': '#c0392b',
  'Medium Risk': '#b7770d',
  'Low Risk': '#1a6b3a',
  'Unscored': '#9aa0ae',
}

function StatCard({ label, value, sub, variant = 'default', icon: IconComp }) {
  return (
    <div className={`kpi-card ${variant}`}>
      {IconComp && (
        <div className="kpi-icon">
          <IconComp />
        </div>
      )}
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{typeof value === 'number' ? value.toLocaleString() : value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

const TOOLTIP_STYLE = {
  background: '#fff',
  border: '1px solid #dde0e6',
  borderRadius: 6,
  fontSize: 12,
  boxShadow: '0 2px 8px rgba(0,0,0,.08)',
}

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
      const r2 = await getDashboardStats()
      setStats(r2.data)
      alert(`${r.data.scored} projects scored successfully.`)
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally {
      setScoring(false)
    }
  }

  if (loading) return <div className="spinner-wrap"><div className="spinner" /></div>
  if (!stats) return <div className="empty-state"><div className="empty-state-text">Failed to load dashboard data.</div></div>

  const pieData = [
    { name: 'High Risk',   value: Number(stats.high_risk) || 0,   color: RISK_COLORS['High Risk'] },
    { name: 'Medium Risk', value: Number(stats.medium_risk) || 0, color: RISK_COLORS['Medium Risk'] },
    { name: 'Low Risk',    value: Number(stats.low_risk) || 0,    color: RISK_COLORS['Low Risk'] },
    { name: 'Unscored',   value: Number(stats.unscored) || 0,   color: RISK_COLORS['Unscored'] },
  ].filter(d => d.value > 0)

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Overview</h1>
          <div className="page-subtitle">Summary of all land acquisition projects and risk indicators</div>
        </div>
        {(user?.role === 'central' || user?.role === 'state') && (
          <button className="btn btn-primary" onClick={handleBatchScore} disabled={scoring} style={{ display: 'none' }}>
            <Icon.Lightning />
            {scoring ? 'Scoring in progress…' : 'Run Batch Score'}
          </button>
        )}
      </div>

      {/* KPI Row */}
      <div className="kpi-grid">
        <StatCard label="Total Projects"    value={stats.total_projects}               icon={Icon.Projects} />
        <StatCard label="High Risk"         value={stats.high_risk}    variant="danger"
          sub="Require immediate attention"  icon={Icon.AlertTriangle} />
        <StatCard label="Medium Risk"       value={stats.medium_risk}  variant="warning" icon={Icon.TrendUp} />
        <StatCard label="Low Risk"          value={stats.low_risk}     variant="success" icon={Icon.Check} />
        <StatCard label="Avg Risk Score"    value={stats.avg_risk_score} sub="out of 100" />
        <StatCard label="Legal Disputes"    value={stats.projects_with_legal_dispute} variant="warning" icon={Icon.Scale} />
        <StatCard label="Avg Compensation"  value={`${stats.avg_compensation_pct}%`}  sub="disbursed" icon={Icon.Wallet} />
        <StatCard label="Avg R&R"           value={`${stats.avg_rr_completion_pct}%`} sub="completed" />
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Risk Distribution */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Risk Distribution</div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                outerRadius={80} innerRadius={40}
                label={({ name, percent }) => percent > 0.04 ? `${(percent*100).toFixed(0)}%` : ''}>
                {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} layout="vertical" align="right" verticalAlign="middle" />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* High Risk by State */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">High Risk Projects by State</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.by_state.slice(0, 8)} layout="vertical" margin={{ left: 80, right: 16 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={80} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="high" fill="#c0392b" name="High" radius={[0, 3, 3, 0]} maxBarSize={12} />
              <Bar dataKey="medium" fill="#b7770d" name="Medium" radius={[0, 3, 3, 0]} maxBarSize={12} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Avg Risk by Project Type */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Average Risk Score by Project Type</div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.by_project_type} layout="vertical" margin={{ left: 110, right: 16 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="project_type" tick={{ fontSize: 10 }} width={110} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}`, 'Avg Risk Score']} />
              <Bar dataKey="avg_risk" fill="#1a3c6e" name="Avg Risk" radius={[0, 3, 3, 0]} maxBarSize={10} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* By Stage */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Projects by Acquisition Stage</div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.by_stage} margin={{ left: 8, right: 8, bottom: 40 }}>
              <XAxis dataKey="stage" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" interval={0} height={60} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#1a3c6e" radius={[3, 3, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom row: High-Risk table + Model Status card */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
        <div className="table-container">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--gray-100)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title">Top High-Risk Projects</div>
            <button className="btn btn-outline btn-sm"
              onClick={() => navigate('/projects?risk_category=High')}>
              View All
            </button>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Project ID</th>
                  <th>Project Name</th>
                  <th>State</th>
                  <th>District</th>
                  <th>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_high_risk.map(p => (
                  <tr key={p.project_id} onClick={() => navigate(`/projects/${p.project_id}`)}>
                    <td><span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{p.project_id}</span></td>
                    <td style={{ fontWeight: 500 }}>{p.project_name}</td>
                    <td>{p.state}</td>
                    <td>{p.district}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div className="progress-wrap" style={{ width: 80 }}>
                          <div className="progress-bar danger" style={{ width: `${p.risk_score}%` }} />
                        </div>
                        <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--danger)' }}>{p.risk_score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <ModelStatusCard />
      </div>
    </>
  )
}

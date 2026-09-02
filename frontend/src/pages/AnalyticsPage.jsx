import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Cell, Legend,
} from 'recharts'
import { getStateAnalytics } from '../services/api'

const TOOLTIP_STYLE = {
  background: '#fff', border: '1px solid var(--gray-200)',
  borderRadius: 6, fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,.08)',
}

const RULE_LABELS = {
  'R-01': 'Compensation', 'R-02': 'R&R',
  'R-03': 'Legal',        'R-04': 'Documentation',
  'R-05': 'Stakeholder',  'R-06': 'Award Overdue',
  'R-07': 'Possession',   'R-08': 'Governance',
}

const RISK_COLORS = {
  high: '#c0392b', medium: '#b7770d', low: '#1a6b3a',
}

export default function AnalyticsPage() {
  const [data, setData]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected] = useState(null)  // state name for radar detail

  useEffect(() => {
    getStateAnalytics()
      .then(r => {
        setData(r.data)
        if (r.data.length > 0) setSelected(r.data[0].state)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="spinner-wrap"><div className="spinner" /></div>
  if (!data.length) return <div className="empty-state"><div className="empty-state-text">No data available.</div></div>

  const selectedState = data.find(d => d.state === selected) || data[0]

  // Radar data for selected state
  const radarData = [
    { metric: 'Compensation',   value: selectedState.avg_compensation_pct },
    { metric: 'R&R',            value: selectedState.avg_rr_pct },
    { metric: 'Documentation',  value: selectedState.avg_doc_pct },
    { metric: 'Stakeholder',    value: selectedState.avg_stakeholder_pct },
    { metric: 'Low Risk %',     value: selectedState.total ? Math.round(selectedState.low / selectedState.total * 100) : 0 },
  ]

  // Rule hit frequency across all states for heatmap
  const allRules = ['R-01','R-02','R-03','R-04','R-05','R-06','R-07','R-08']
  const ruleBarData = allRules.map(r => ({
    rule:  r,
    label: RULE_LABELS[r],
    count: data.reduce((sum, s) => sum + (s.rule_hits?.[r] || 0), 0),
  })).sort((a, b) => b.count - a.count)

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">State Comparison Analytics</h1>
          <div className="page-subtitle">
            Risk scores, rule violations and acquisition health across all states
          </div>
        </div>
      </div>

      {/* ── Row 1: Avg Risk Score + Delay Rate by State ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Average Risk Score by State</div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} layout="vertical" margin={{ left: 100, right: 40 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={100} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [`${v}`, 'Avg Risk Score']} />
              <Bar dataKey="avg_risk_score" radius={[0, 3, 3, 0]} maxBarSize={12}>
                {data.map((d, i) => (
                  <Cell key={i} fill={d.avg_risk_score >= 70 ? RISK_COLORS.high : d.avg_risk_score >= 40 ? RISK_COLORS.medium : RISK_COLORS.low} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Delay Rate by State (%)</div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} layout="vertical" margin={{ left: 100, right: 40 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={100} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [`${v}%`, 'Delay Rate']} />
              <Bar dataKey="delay_rate" radius={[0, 3, 3, 0]} maxBarSize={12} fill="var(--primary)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Row 2: Risk Stack + Rule Frequency ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Risk Distribution by State</div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} layout="vertical" margin={{ left: 100, right: 8 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={100} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="high"   stackId="a" fill={RISK_COLORS.high}   name="High"   maxBarSize={12} />
              <Bar dataKey="medium" stackId="a" fill={RISK_COLORS.medium} name="Medium" maxBarSize={12} />
              <Bar dataKey="low"    stackId="a" fill={RISK_COLORS.low}    name="Low"    maxBarSize={12} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Most Triggered Rules (All States)</div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={ruleBarData} margin={{ left: 8, right: 8, bottom: 30 }}>
              <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" interval={0} height={50} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n, p) => [v, `${p.payload.rule} — ${p.payload.label}`]} />
              <Bar dataKey="count" fill="var(--primary)" radius={[3, 3, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Row 3: State drill-down ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 20, marginBottom: 20 }}>
        {/* State selector */}
        <div className="card" style={{ padding: '12px 0' }}>
          <div style={{ padding: '0 16px 10px', fontSize: 11, fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--gray-400)' }}>
            Select State
          </div>
          {data.map(d => (
            <div key={d.state}
              onClick={() => setSelected(d.state)}
              style={{
                padding: '8px 16px', cursor: 'pointer', fontSize: 13,
                fontWeight: selected === d.state ? 600 : 400,
                background: selected === d.state ? 'var(--primary-light)' : 'transparent',
                color: selected === d.state ? 'var(--primary)' : 'var(--gray-700)',
                borderLeft: selected === d.state ? '3px solid var(--primary)' : '3px solid transparent',
                transition: 'all .1s',
              }}>
              {d.state}
            </div>
          ))}
        </div>

        {/* State detail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Total Projects', value: selectedState.total },
              { label: 'High Risk',      value: selectedState.high,   color: 'var(--danger)' },
              { label: 'Delay Rate',     value: `${selectedState.delay_rate}%`, color: 'var(--warning)' },
              { label: 'Avg Risk Score', value: selectedState.avg_risk_score },
            ].map(k => (
              <div key={k.label} className="card" style={{ padding: '14px 16px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '.06em', color: 'var(--gray-400)', marginBottom: 6 }}>
                  {k.label}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color: k.color || 'var(--gray-800)' }}>
                  {k.value}
                </div>
              </div>
            ))}
          </div>

          {/* Progress bars + Radar */}
          <div className="grid-2">
            <div className="card">
              <div className="detail-section-title">Acquisition Health Indicators</div>
              {[
                { label: 'Avg Compensation (R-01)', value: selectedState.avg_compensation_pct, threshold: 50 },
                { label: 'Avg R&R (R-02)',           value: selectedState.avg_rr_pct,           threshold: 50 },
                { label: 'Avg Documentation (R-04)', value: selectedState.avg_doc_pct,          threshold: 60 },
                { label: 'Avg Stakeholder (R-05)',   value: selectedState.avg_stakeholder_pct,  threshold: 50 },
              ].map(({ label, value, threshold }) => {
                const bad   = value < threshold
                const color = bad ? 'var(--danger)' : value < threshold * 1.4 ? 'var(--warning)' : 'var(--success)'
                return (
                  <div key={label} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 11, color: 'var(--gray-500)' }}>{label}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color }}>{value}%</span>
                    </div>
                    <div className="progress-wrap">
                      <div className="progress-bar" style={{ width: `${value}%`,
                        background: color }} />
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="card">
              <div className="detail-section-title">Health Radar — {selectedState.state}</div>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData} margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
                  <PolarGrid stroke="var(--gray-200)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: 'var(--gray-500)' }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} axisLine={false} />
                  <Radar dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Rule hit table for selected state */}
          <div className="card">
            <div className="detail-section-title">Rule Violations in {selectedState.state}</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {allRules.map(r => {
                const count = selectedState.rule_hits?.[r] || 0
                const pct   = selectedState.total ? Math.round(count / selectedState.total * 100) : 0
                return (
                  <div key={r} style={{
                    padding: '10px 12px', borderRadius: 'var(--radius)',
                    background: count > 0 ? 'var(--danger-light)' : 'var(--gray-50)',
                    border: `1px solid ${count > 0 ? 'var(--danger-border)' : 'var(--gray-200)'}`,
                  }}>
                    <div style={{ fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                      color: count > 0 ? 'var(--danger)' : 'var(--gray-400)', marginBottom: 4 }}>
                      {r}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--gray-500)', marginBottom: 6 }}>
                      {RULE_LABELS[r]}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 800,
                      color: count > 0 ? 'var(--danger)' : 'var(--gray-300)' }}>
                      {count}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--gray-400)' }}>{pct}% of projects</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── Summary table ── */}
      <div className="table-container">
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--gray-100)' }}>
          <div className="card-title">All States — Summary</div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>State</th><th>Total</th><th>High</th><th>Med</th>
                <th>Avg Risk</th><th>Delay Rate</th>
                <th>Avg Comp%</th><th>Avg R&R%</th><th>Avg Doc%</th>
                <th>Rules Hit</th>
              </tr>
            </thead>
            <tbody>
              {data.map(d => (
                <tr key={d.state}
                  style={{ cursor: 'pointer', background: selected === d.state ? 'var(--primary-light)' : '' }}
                  onClick={() => setSelected(d.state)}>
                  <td style={{ fontWeight: 600 }}>{d.state}</td>
                  <td>{d.total}</td>
                  <td style={{ color: 'var(--danger)', fontWeight: 600 }}>{d.high}</td>
                  <td style={{ color: 'var(--warning)' }}>{d.medium}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="progress-wrap" style={{ width: 50 }}>
                        <div className="progress-bar" style={{ width: `${d.avg_risk_score}%`,
                          background: d.avg_risk_score >= 70 ? 'var(--danger)' : d.avg_risk_score >= 40 ? 'var(--warning)' : 'var(--success)' }} />
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 700 }}>{d.avg_risk_score}</span>
                    </div>
                  </td>
                  <td style={{ color: d.delay_rate > 60 ? 'var(--danger)' : 'inherit' }}>{d.delay_rate}%</td>
                  <td style={{ color: d.avg_compensation_pct < 50 ? 'var(--danger)' : 'inherit' }}>{d.avg_compensation_pct}%</td>
                  <td style={{ color: d.avg_rr_pct < 50 ? 'var(--danger)' : 'inherit' }}>{d.avg_rr_pct}%</td>
                  <td style={{ color: d.avg_doc_pct < 60 ? 'var(--danger)' : 'inherit' }}>{d.avg_doc_pct}%</td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                      {Object.entries(d.rule_hits || {})
                        .filter(([, v]) => v > 0)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(([r, v]) => (
                          <span key={r} style={{
                            fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 700,
                            padding: '1px 4px', borderRadius: 2,
                            background: 'var(--danger-light)', color: 'var(--danger)',
                          }}>{r}:{v}</span>
                        ))
                      }
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

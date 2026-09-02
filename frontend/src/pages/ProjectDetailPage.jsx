import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProject, scoreProject } from '../services/api'

function RiskBadge({ cat }) {
  if (!cat) return <span className="badge badge-none">Unscored</span>
  return <span className={`badge badge-${cat}`} style={{ fontSize: 14, padding: '4px 12px' }}>{cat} Risk</span>
}

function ShapChart({ factors }) {
  if (!factors?.length) return null
  const maxAbs = Math.max(...factors.map(f => Math.abs(f.shap_value)), 0.001)

  return (
    <div>
      {factors.map((f, i) => {
        const pct = (Math.abs(f.shap_value) / maxAbs) * 45
        const isPos = f.shap_value > 0
        return (
          <div key={i} className="shap-row">
            <div className="shap-label" title={f.display_name}>{f.display_name}</div>
            <div className="shap-bar-wrap">
              {isPos
                ? <div className="shap-bar-pos" style={{ width: `${pct}%` }} />
                : <div className="shap-bar-neg" style={{ width: `${pct}%` }} />
              }
              <div style={{ position: 'absolute', top: '50%', left: '50%', width: 1, height: '100%', transform: 'translateY(-50%)', background: '#cbd5e1' }} />
            </div>
            <div className={`shap-val ${isPos ? 'pos' : 'neg'}`}>
              {f.shap_value > 0 ? '+' : ''}{f.shap_value.toFixed(3)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div className="detail-field">
      <div className="detail-field-label">{label}</div>
      <div className="detail-field-value">{value ?? '—'}</div>
    </div>
  )
}

export default function ProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scoring, setScoring] = useState(false)

  useEffect(() => {
    getProject(id)
      .then(r => setProject(r.data))
      .finally(() => setLoading(false))
  }, [id])

  async function handleScore() {
    setScoring(true)
    try {
      await scoreProject(id)
      const r = await getProject(id)
      setProject(r.data)
    } catch (e) {
      alert('Scoring failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setScoring(false)
    }
  }

  if (loading) return <div className="spinner" />
  if (!project) return <div className="empty-state">Project not found.</div>

  const shap = project.shap_factors || []
  const recs = project.recommendations || []
  const reasons = Array.isArray(project.top_delay_reasons) ? project.top_delay_reasons : []

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-outline btn-sm" onClick={() => navigate(-1)}>← Back</button>
        <h1 className="page-title" style={{ margin: 0 }}>{project.project_name}</h1>
        <code style={{ fontSize: 12, color: 'var(--gray-500)', background: 'var(--gray-100)', padding: '2px 8px', borderRadius: 4 }}>{project.project_id}</code>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Left column */}
        <div>
          {/* Risk Score Card */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 8 }}>AI Risk Assessment</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <RiskBadge cat={project.risk_category} />
                  {project.risk_score != null && (
                    <span style={{ fontSize: 32, fontWeight: 700, color: project.risk_category === 'High' ? 'var(--danger)' : project.risk_category === 'Medium' ? 'var(--warning)' : 'var(--success)' }}>
                      {project.risk_score} <span style={{ fontSize: 14, fontWeight: 400, color: 'var(--gray-500)' }}>/ 100</span>
                    </span>
                  )}
                </div>
                {project.risk_score != null && (
                  <div className="risk-bar-wrap" style={{ width: 300 }}>
                    <div className={`risk-bar ${project.risk_category}`} style={{ width: `${project.risk_score}%` }} />
                  </div>
                )}
                {project.delay_probability != null && (
                  <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8 }}>
                    Delay probability: <strong>{(project.delay_probability * 100).toFixed(1)}%</strong>
                    {project.last_scored_at && <span> · Scored: {new Date(project.last_scored_at).toLocaleDateString()}</span>}
                  </div>
                )}
              </div>
              <button className="btn btn-primary" onClick={handleScore} disabled={scoring}>
                {scoring ? 'Scoring…' : '⚡ Re-score'}
              </button>
            </div>
          </div>

          {/* SHAP Explanation */}
          {shap.length > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title">Why this risk score? (SHAP Explanation)</div>
              <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 12 }}>
                <span style={{ color: 'var(--danger)' }}>■</span> increases risk &nbsp;
                <span style={{ color: '#3b82f6' }}>■</span> decreases risk
              </div>
              <ShapChart factors={shap} />
            </div>
          )}

          {/* Recommendations */}
          {recs.length > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title">Recommended Actions</div>
              {recs.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, padding: '10px 12px', background: '#fffbeb', borderRadius: 6, border: '1px solid #fde68a' }}>
                  <span style={{ fontSize: 16 }}>💡</span>
                  <span style={{ fontSize: 13 }}>{r}</span>
                </div>
              ))}
            </div>
          )}

          {/* Project Details */}
          <div className="card">
            <div className="card-title">Project Details</div>
            <div className="detail-grid">
              <Field label="Project Type"     value={project.project_type} />
              <Field label="State"            value={project.state} />
              <Field label="District"         value={project.district} />
              <Field label="Start Date"       value={project.start_date} />
              <Field label="Land Area"        value={project.land_area_ha ? `${project.land_area_ha.toLocaleString()} ha` : null} />
              <Field label="Families Affected" value={project.families_affected?.toLocaleString()} />
              <Field label="Current Stage"    value={project.current_stage} />
              <Field label="Days in Stage"    value={project.days_in_current_stage ? `${project.days_in_current_stage} days` : null} />
              <Field label="Days Since Action" value={project.days_since_last_action ? `${project.days_since_last_action} days` : null} />
              <Field label="Pending Approvals" value={project.pending_approvals} />
            </div>
          </div>
        </div>

        {/* Right column */}
        <div>
          {/* Financial */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Compensation & Finance</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 4 }}>Compensation Disbursed</div>
              <div className="risk-bar-wrap">
                <div className="risk-bar" style={{ width: `${project.compensation_pct || 0}%`, background: project.compensation_pct < 50 ? 'var(--danger)' : project.compensation_pct < 80 ? 'var(--warning)' : 'var(--success)' }} />
              </div>
              <div style={{ font: '600 20px/1 sans-serif', marginTop: 6 }}>{project.compensation_pct}%</div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 4 }}>R&R Completion</div>
              <div className="risk-bar-wrap">
                <div className="risk-bar" style={{ width: `${project.rr_completion_pct || 0}%`, background: project.rr_completion_pct < 50 ? 'var(--danger)' : project.rr_completion_pct < 80 ? 'var(--warning)' : 'var(--success)' }} />
              </div>
              <div style={{ font: '600 20px/1 sans-serif', marginTop: 6 }}>{project.rr_completion_pct}%</div>
            </div>
            <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <Field label="Land Cost" value={project.land_cost_cr ? `₹${project.land_cost_cr} Cr` : null} />
              <Field label="Paid So Far" value={project.amount_paid_cr ? `₹${project.amount_paid_cr} Cr` : null} />
              <Field label="Project Value" value={project.project_value_cr ? `₹${project.project_value_cr} Cr` : null} />
              <Field label="Budget Released" value={project.budget_released ? '✅ Yes' : '❌ No'} />
            </div>
          </div>

          {/* Legal & Admin */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Legal & Administrative</div>
            <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <Field label="Legal Dispute" value={project.has_legal_dispute ? '⚠️ Yes' : 'No'} />
              <Field label="Legal Cases" value={project.num_legal_cases} />
              <Field label="Pending Notifications" value={project.pending_notifications} />
              <Field label="NOC Pending" value={project.noc_pending_count} />
              <Field label="Possession" value={project.possession_pct != null ? `${project.possession_pct}%` : null} />
              <Field label="Officer Score" value={project.officer_responsiveness ? `${project.officer_responsiveness}/10` : null} />
            </div>
          </div>

          {/* Known Delay Reasons */}
          {reasons.length > 0 && (
            <div className="card">
              <div className="card-title">Known Delay Factors</div>
              {reasons.map((r, i) => (
                <div key={i} className="chip" style={{ display: 'block', margin: '4px 0' }}>⚠ {r}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../services/api'
import { Icon } from '../components/shared/Icons'

const PROJECT_TYPES = [
  'National Highway','State Highway','Railway Line','Metro Rail','Expressway',
  'Dam / Reservoir','Irrigation Canal','Industrial Corridor','Power Plant',
  'Solar Park','Transmission Line','Airport Expansion','Port Development',
  'Smart City','Housing Scheme',
]
const STATES = [
  'Andhra Pradesh','Bihar','Gujarat','Haryana','Jharkhand','Karnataka',
  'Madhya Pradesh','Maharashtra','Odisha','Punjab','Rajasthan','Tamil Nadu',
  'Telangana','Uttar Pradesh','West Bengal',
]
const STAGES = [
  'Section 11 Notification','Section 19 Declaration','Award Passed',
  'Compensation Disbursed','Possession Taken','R&R Completed',
]

const RISK_COLOR = { High: 'var(--danger)', Medium: 'var(--warning)', Low: 'var(--success)' }
const RISK_BG    = { High: 'var(--danger-light)', Medium: 'var(--warning-light)', Low: 'var(--success-light)' }

// ─── Field helper ─────────────────────────────────────────────────────────────
function Field({ label, required, children, hint }) {
  return (
    <div className="field">
      <label className="field-label">
        {label}{required && <span style={{ color: 'var(--danger)', marginLeft: 2 }}>*</span>}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 3 }}>{hint}</div>}
    </div>
  )
}

function Input({ name, value, onChange, type = 'text', ...rest }) {
  return (
    <input className="field-input" name={name} value={value}
      onChange={onChange} type={type} {...rest} />
  )
}

function Select({ name, value, onChange, children }) {
  return (
    <select className="field-input" name={name} value={value} onChange={onChange}>
      {children}
    </select>
  )
}

// ─── SHAP bar ─────────────────────────────────────────────────────────────────
function ShapRow({ factor }) {
  const maxPct = 40
  const pct    = Math.min(Math.abs(factor.shap_value) * 80, maxPct)
  const isPos  = factor.shap_value > 0
  return (
    <div className="shap-row">
      <div className="shap-label">{factor.display_name}</div>
      <div className="shap-track">
        <div className="shap-center-line" />
        {isPos
          ? <div className="shap-fill-pos" style={{ width: `${pct}%` }} />
          : <div className="shap-fill-neg" style={{ width: `${pct}%` }} />
        }
      </div>
      <div className={`shap-value ${isPos ? 'pos' : 'neg'}`}>
        {factor.shap_value > 0 ? '+' : ''}{factor.shap_value.toFixed(3)}
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SubmitProjectPage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult]         = useState(null)   // AI response after submit
  const [error, setError]           = useState('')

  const [form, setForm] = useState({
    project_name: '', project_type: 'National Highway', state: 'Uttar Pradesh',
    district: '', start_date: '', land_area_ha: '', families_affected: '',
    current_stage: 'Section 11 Notification',
    days_in_current_stage: '0', days_since_last_action: '0',
    pending_approvals: '0', pending_notifications: '0',
    has_legal_dispute: false, num_legal_cases: '0', ownership_conflicts: '0',
    compensation_pct: '0', compensation_pending_months: '0',
    rr_completion_pct: '0', possession_pct: '0',
    documentation_pct: '75', stakeholder_response_pct: '75',
    budget_released: true, noc_pending_count: '0',
    land_cost_cr: '0', amount_paid_cr: '0', project_value_cr: '0',
    officer_responsiveness: '5', latitude: '', longitude: '',
  })

  function set(e) {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        land_area_ha:                parseFloat(form.land_area_ha),
        families_affected:           parseInt(form.families_affected),
        days_in_current_stage:       parseInt(form.days_in_current_stage) || 0,
        days_since_last_action:      parseInt(form.days_since_last_action) || 0,
        pending_approvals:           parseInt(form.pending_approvals) || 0,
        pending_notifications:       parseInt(form.pending_notifications) || 0,
        num_legal_cases:             parseInt(form.num_legal_cases) || 0,
        ownership_conflicts:         parseInt(form.ownership_conflicts) || 0,
        compensation_pct:            parseFloat(form.compensation_pct) || 0,
        compensation_pending_months: parseInt(form.compensation_pending_months) || 0,
        rr_completion_pct:           parseFloat(form.rr_completion_pct) || 0,
        possession_pct:              parseFloat(form.possession_pct) || 0,
        documentation_pct:           parseFloat(form.documentation_pct) || 75,
        stakeholder_response_pct:    parseFloat(form.stakeholder_response_pct) || 75,
        noc_pending_count:           parseInt(form.noc_pending_count) || 0,
        land_cost_cr:                parseFloat(form.land_cost_cr) || 0,
        amount_paid_cr:              parseFloat(form.amount_paid_cr) || 0,
        project_value_cr:            parseFloat(form.project_value_cr) || 0,
        officer_responsiveness:      parseFloat(form.officer_responsiveness) || 5,
        latitude:  form.latitude  ? parseFloat(form.latitude)  : null,
        longitude: form.longitude ? parseFloat(form.longitude) : null,
      }
      const { data } = await createProject(payload)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Submission failed. Please check the form.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Result screen (shown after successful submission) ──────────────────────
  if (result) {
    const cat = result.risk_category
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24, fontSize: 13, color: 'var(--gray-500)' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/projects')}>
            <Icon.ChevronLeft /> Back to Projects
          </button>
        </div>

        {/* Result hero */}
        <div className="card" style={{ marginBottom: 20, borderTop: `4px solid ${RISK_COLOR[cat]}`, background: RISK_BG[cat] }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', color: RISK_COLOR[cat], marginBottom: 6 }}>
                AI Risk Assessment Complete
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 4 }}>
                {result.project_name}
              </div>
              <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 16 }}>
                {result.district}, {result.state} &nbsp;·&nbsp;
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, background: 'rgba(0,0,0,.06)', padding: '1px 6px', borderRadius: 3 }}>{result.project_id}</span>
              </div>
              <span className={`risk-badge ${cat}`} style={{ fontSize: 13, padding: '5px 14px' }}>
                <span className={`risk-dot ${cat}`} />
                {cat} Risk
              </span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 56, fontWeight: 800, lineHeight: 1, color: RISK_COLOR[cat] }}>
                {result.risk_score}
              </div>
              <div style={{ fontSize: 14, color: 'var(--gray-400)' }}>out of 100</div>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>
                Delay probability: <strong style={{ color: RISK_COLOR[cat] }}>
                  {(result.delay_probability * 100).toFixed(1)}%
                </strong>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* SHAP explanation */}
          <div className="card">
            <div className="detail-section-title">Why this risk score? (Live SHAP Analysis)</div>
            <div style={{ display: 'flex', fontSize: 11, color: 'var(--gray-400)', marginBottom: 12, gap: 16 }}>
              <span><span style={{ display:'inline-block', width:10, height:4, borderRadius:2, background:'var(--danger)', marginRight:4 }} />Increases risk</span>
              <span><span style={{ display:'inline-block', width:10, height:4, borderRadius:2, background:'#2563eb', marginRight:4 }} />Reduces risk</span>
            </div>
            {(result.top_factors || []).slice(0, 8).map((f, i) => (
              <ShapRow key={i} factor={f} />
            ))}
          </div>

          {/* Recommendations */}
          <div>
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="detail-section-title">Recommended Actions</div>
              {(result.recommendations || []).map((r, i) => (
                <div key={i} className="rec-item">
                  <div className="rec-icon"><Icon.AlertTriangle /></div>
                  <div className="rec-text">{r}</div>
                </div>
              ))}
              {(!result.recommendations || result.recommendations.length === 0) && (
                <div style={{ color: 'var(--success)', fontSize: 13 }}>No critical issues detected.</div>
              )}
            </div>

            <div className="card">
              <div className="detail-section-title">Next Steps</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button className="btn btn-primary"
                  onClick={() => navigate(`/projects/${result.project_id}`)}>
                  View Full Project Detail
                </button>
                <button className="btn btn-outline"
                  onClick={() => { setResult(null); setForm(f => ({ ...f, project_name: '', district: '' })) }}>
                  Submit Another Project
                </button>
                <button className="btn btn-ghost"
                  onClick={() => navigate('/projects')}>
                  Back to All Projects
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Form screen ────────────────────────────────────────────────────────────
  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Submit New Project</h1>
          <div className="page-subtitle">
            Fill in project details — AI will score delay risk instantly on submission
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/projects')}>
          <Icon.ChevronLeft /> Cancel
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', background: 'var(--danger-light)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: 13, marginBottom: 20 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>

          {/* ── Left: main fields ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Basic info */}
            <div className="card">
              <div className="detail-section-title">Project Information</div>
              <div className="detail-grid">
                <div style={{ gridColumn: '1 / -1' }}>
                  <Field label="Project Name" required>
                    <Input name="project_name" value={form.project_name} onChange={set}
                      required placeholder="e.g. NH-48 Expressway Widening, Lucknow" />
                  </Field>
                </div>
                <Field label="Project Type" required>
                  <Select name="project_type" value={form.project_type} onChange={set}>
                    {PROJECT_TYPES.map(t => <option key={t}>{t}</option>)}
                  </Select>
                </Field>
                <Field label="Start Date">
                  <Input name="start_date" value={form.start_date} onChange={set} type="date" />
                </Field>
                <Field label="State" required>
                  <Select name="state" value={form.state} onChange={set}>
                    {STATES.map(s => <option key={s}>{s}</option>)}
                  </Select>
                </Field>
                <Field label="District" required>
                  <Input name="district" value={form.district} onChange={set}
                    required placeholder="e.g. Lucknow" />
                </Field>
                <Field label="Latitude" hint="Optional — for GIS map display">
                  <Input name="latitude" value={form.latitude} onChange={set} type="number" step="any" placeholder="e.g. 26.85" />
                </Field>
                <Field label="Longitude">
                  <Input name="longitude" value={form.longitude} onChange={set} type="number" step="any" placeholder="e.g. 80.95" />
                </Field>
                <Field label="Land Area (hectares)" required>
                  <Input name="land_area_ha" value={form.land_area_ha} onChange={set}
                    type="number" step="0.01" min="0.01" required placeholder="e.g. 250.5" />
                </Field>
                <Field label="Families Affected" required>
                  <Input name="families_affected" value={form.families_affected} onChange={set}
                    type="number" min="0" required placeholder="e.g. 480" />
                </Field>
              </div>
            </div>

            {/* Acquisition stage */}
            <div className="card">
              <div className="detail-section-title">Acquisition Progress</div>
              <div className="detail-grid">
                <Field label="Current Stage" required>
                  <Select name="current_stage" value={form.current_stage} onChange={set}>
                    {STAGES.map(s => <option key={s}>{s}</option>)}
                  </Select>
                </Field>
                <Field label="Days in Current Stage">
                  <Input name="days_in_current_stage" value={form.days_in_current_stage} onChange={set} type="number" min="0" />
                </Field>
                <Field label="Days Since Last Action" hint="Higher = more stagnant">
                  <Input name="days_since_last_action" value={form.days_since_last_action} onChange={set} type="number" min="0" />
                </Field>
                <Field label="Pending Approvals">
                  <Input name="pending_approvals" value={form.pending_approvals} onChange={set} type="number" min="0" />
                </Field>
                <Field label="Pending Notifications">
                  <Input name="pending_notifications" value={form.pending_notifications} onChange={set} type="number" min="0" />
                </Field>
                <Field label="NOC Pending (Depts)">
                  <Input name="noc_pending_count" value={form.noc_pending_count} onChange={set} type="number" min="0" />
                </Field>
              </div>
            </div>

            {/* Legal */}
            <div className="card">
              <div className="detail-section-title">Legal Status (R-03)</div>
              <div className="detail-grid">
                <Field label="Active Legal Dispute">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
                    <input type="checkbox" name="has_legal_dispute"
                      checked={form.has_legal_dispute} onChange={set}
                      style={{ width: 16, height: 16, cursor: 'pointer' }} />
                    <span style={{ fontSize: 13, color: 'var(--gray-600)' }}>
                      {form.has_legal_dispute ? 'Yes — active dispute' : 'No dispute'}
                    </span>
                  </div>
                </Field>
                <Field label="Number of Legal Cases">
                  <Input name="num_legal_cases" value={form.num_legal_cases} onChange={set} type="number" min="0" />
                </Field>
                <Field label="Ownership Conflicts" hint="R-03: triggers if ≥ 3">
                  <Input name="ownership_conflicts" value={form.ownership_conflicts} onChange={set} type="number" min="0" />
                </Field>
              </div>
            </div>
          </div>

          {/* ── Right: financial + context ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            <div className="card">
              <div className="detail-section-title">Compensation & R&R</div>
              <Field label="Compensation Disbursed (%)" hint="R-01: triggers if < 50%">
                <Input name="compensation_pct" value={form.compensation_pct} onChange={set}
                  type="number" min="0" max="100" step="0.1" />
              </Field>
              <Field label="Months Compensation Pending">
                <Input name="compensation_pending_months" value={form.compensation_pending_months} onChange={set} type="number" min="0" />
              </Field>
              <Field label="R&R Completion (%)" hint="R-02: triggers if < 50%">
                <Input name="rr_completion_pct" value={form.rr_completion_pct} onChange={set}
                  type="number" min="0" max="100" step="0.1" />
              </Field>
              <Field label="Possession Taken (%)">
                <Input name="possession_pct" value={form.possession_pct} onChange={set}
                  type="number" min="0" max="100" step="0.1" />
              </Field>
              <Field label="Documentation Complete (%)" hint="R-04: triggers if < 60%">
                <Input name="documentation_pct" value={form.documentation_pct} onChange={set}
                  type="number" min="0" max="100" step="0.1" />
              </Field>
              <Field label="Stakeholder Response (%)" hint="R-05: triggers if < 50%">
                <Input name="stakeholder_response_pct" value={form.stakeholder_response_pct} onChange={set}
                  type="number" min="0" max="100" step="0.1" />
              </Field>
              <Field label="Budget Released">
                <Select name="budget_released" value={String(form.budget_released)} onChange={e => setForm(f => ({ ...f, budget_released: e.target.value === 'true' }))}>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </Select>
              </Field>
            </div>

            <div className="card">
              <div className="detail-section-title">Financial (in Crores)</div>
              <Field label="Total Land Cost (Cr)">
                <Input name="land_cost_cr" value={form.land_cost_cr} onChange={set} type="number" min="0" step="0.01" />
              </Field>
              <Field label="Amount Paid So Far (Cr)">
                <Input name="amount_paid_cr" value={form.amount_paid_cr} onChange={set} type="number" min="0" step="0.01" />
              </Field>
              <Field label="Total Project Value (Cr)">
                <Input name="project_value_cr" value={form.project_value_cr} onChange={set} type="number" min="0" step="0.01" />
              </Field>
            </div>

            <div className="card">
              <div className="detail-section-title">Context</div>
              <Field label="Officer Responsiveness (1–10)" hint="10 = highly responsive">
                <Input name="officer_responsiveness" value={form.officer_responsiveness} onChange={set}
                  type="number" min="1" max="10" step="0.1" />
              </Field>
            </div>

            {/* AI notice */}
            <div style={{ padding: '14px 16px', background: 'var(--primary-light)', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 6 }}>
                Live AI Scoring
              </div>
              <div style={{ fontSize: 12, color: 'var(--gray-600)', lineHeight: 1.6 }}>
                On submission, the XGBoost model will run live inference on your inputs, compute SHAP values for each risk factor, and return a risk score + recommended actions — in real time.
              </div>
            </div>

            <button className="btn btn-primary btn-lg"
              type="submit" disabled={submitting}
              style={{ justifyContent: 'center', width: '100%' }}>
              {submitting
                ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2, margin: 0 }} /> Running AI Assessment…</>
                : <><Icon.Lightning /> Submit & Score Project</>
              }
            </button>
          </div>
        </div>
      </form>
    </>
  )
}

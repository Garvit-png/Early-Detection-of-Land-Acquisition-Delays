import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, ReferenceLine, Cell,
} from 'recharts'
import {
  getProject, scoreProject, updateProject,
  getRiskHistory, getSimilarProjects, getProjectActions,
  createAction, updateAction, getExplanation, getStageWisePrediction,
  getStageWiseExplanation, getOverallExplanation, chatWithProject,
} from '../services/api'
import { Icon } from '../components/shared/Icons'

// ─── Constants ────────────────────────────────────────────────────────────────
const STAGES = [
  'Section 11 Notification', 'Section 19 Declaration', 'Award Passed',
  'Compensation Disbursed', 'Possession Taken', 'R&R Completed',
]
const STAGE_EXPECTED = [60, 90, 120, 90, 60, 180]

const RISK_COLOR = { High: 'var(--danger)', Medium: 'var(--warning)', Low: 'var(--success)' }
const PRIORITY_COLOR = { critical: '#7c0000', high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--success)' }
const STATUS_COLOR   = { open: 'var(--warning)', in_progress: 'var(--primary)', completed: 'var(--success)', overridden: 'var(--gray-400)' }

// ─── Shared sub-components ────────────────────────────────────────────────────
function RiskBadge({ cat, large }) {
  if (!cat) return <span className="risk-badge none">Not Scored</span>
  return (
    <span className={`risk-badge ${cat}`} style={large ? { fontSize: 13, padding: '5px 14px' } : {}}>
      <span className={`risk-dot ${cat}`} />{cat} Risk
    </span>
  )
}

function RuleBadge({ ruleId }) {
  const labels = { 'R-01':'Compensation','R-02':'R&R','R-03':'Legal','R-04':'Documentation','R-05':'Stakeholder','R-06':'Award Overdue','R-07':'Possession','R-08':'Governance' }
  return (
    <span title={labels[ruleId]} style={{
      display:'inline-flex', alignItems:'center', gap:3, padding:'2px 7px',
      borderRadius:3, marginRight:4, marginBottom:4,
      background:'var(--danger-light)', color:'var(--danger)',
      border:'1px solid var(--danger-border)', fontSize:11, fontWeight:700,
      fontFamily:'var(--font-mono)',
    }}>
      {ruleId}<span style={{fontSize:9,fontFamily:'var(--font)',marginLeft:2}}>{labels[ruleId]}</span>
    </span>
  )
}

function Field({ label, value, highlight, span2 }) {
  return (
    <div style={span2 ? { gridColumn:'1/-1' } : {}}>
      <div className="detail-field-label">{label}</div>
      <div className="detail-field-value" style={highlight ? { color: highlight } : {}}>{value ?? '—'}</div>
    </div>
  )
}

function ProgressField({ label, value, threshold = 50 }) {
  const v = value ?? 0
  const color = v < threshold ? 'danger' : v < threshold * 1.5 ? 'warning' : 'success'
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
        <span className="detail-field-label">{label}</span>
        <span style={{ fontSize:12, fontWeight:700, color:`var(--${color})` }}>{v}%</span>
      </div>
      <div className="progress-wrap"><div className={`progress-bar ${color}`} style={{ width:`${v}%` }} /></div>
    </div>
  )
}

// ─── AI Explanation helper components ─────────────────────────────────────────

function LoadingCard({ text }) {
  return (
    <div className="card" style={{ padding:32, textAlign:'center' }}>
      <div className="spinner" style={{ margin:'0 auto 12px' }} />
      <div style={{ fontSize:13, color:'var(--gray-500)' }}>{text}</div>
    </div>
  )
}

function ErrorCard({ msg }) {
  return (
    <div className="card" style={{ padding:16, background:'var(--danger-light)', border:'1px solid var(--danger-border)' }}>
      <div style={{ fontSize:13, fontWeight:700, color:'var(--danger)', marginBottom:4 }}>Request failed</div>
      <div style={{ fontSize:12, color:'var(--danger)' }}>{msg}</div>
    </div>
  )
}

function ModelBadge({ model, tokens, chunks, tiny }) {
  const isGpt = model === 'gpt-4o-mini'
  return (
    <div style={{ display:'flex', alignItems:'center', gap:6, flexShrink:0 }}>
      <span style={{
        fontSize: tiny ? 9 : 10, fontWeight:700, padding: tiny ? '1px 5px' : '2px 8px',
        borderRadius:3,
        background: isGpt ? '#e0f2fe' : 'var(--gray-100)',
        color: isGpt ? '#0369a1' : 'var(--gray-500)',
        border: isGpt ? '1px solid #7dd3fc' : '1px solid var(--gray-200)',
      }}>
        {isGpt ? 'GPT-4o-mini' : 'Fallback'}
      </span>
      {!tiny && tokens > 0 && <span style={{ fontSize:10, color:'var(--gray-400)' }}>{tokens} tok</span>}
      {!tiny && chunks > 0 && <span style={{ fontSize:10, color:'var(--gray-400)' }}>{chunks} chunks</span>}
    </div>
  )
}

function ExplainSection({ title, color, text, footer }) {
  return (
    <div style={{ marginBottom:14, paddingBottom:14, borderBottom:'1px solid var(--gray-100)' }}>
      <div style={{ fontSize:11, fontWeight:700, textTransform:'uppercase', letterSpacing:'.06em', color: color || 'var(--gray-600)', marginBottom:6 }}>
        {title}
      </div>
      <div style={{ fontSize:13, color:'var(--gray-700)', lineHeight:1.8, whiteSpace:'pre-wrap' }}>{text}</div>
      {footer && <div style={{ marginTop:8, fontSize:11, color:'var(--gray-400)' }}>{footer}</div>}
    </div>
  )
}

function ShapChart({ factors }) {
  if (!factors?.length) return null
  const maxAbs = Math.max(...factors.map(f => Math.abs(f.shap_value)), 0.001)
  return (
    <div>
      <div style={{ display:'flex', fontSize:11, color:'var(--gray-400)', marginBottom:10, justifyContent:'flex-end', gap:16 }}>
        <span><span style={{ display:'inline-block', width:10, height:4, borderRadius:2, background:'var(--danger)', marginRight:4 }} />Increases risk</span>
        <span><span style={{ display:'inline-block', width:10, height:4, borderRadius:2, background:'#2563eb', marginRight:4 }} />Reduces risk</span>
      </div>
      {factors.map((f, i) => {
        const pct = (Math.abs(f.shap_value) / maxAbs) * 44
        const pos = f.shap_value > 0
        return (
          <div key={i} className="shap-row">
            <div className="shap-label" title={f.display_name}>{f.display_name}</div>
            <div className="shap-track">
              <div className="shap-center-line" />
              {pos ? <div className="shap-fill-pos" style={{ width:`${pct}%` }} /> : <div className="shap-fill-neg" style={{ width:`${pct}%` }} />}
            </div>
            <div className={`shap-value ${pos?'pos':'neg'}`}>{f.shap_value>0?'+':''}{f.shap_value.toFixed(3)}</div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Stage Timeline ───────────────────────────────────────────────────────────
function StageTimeline({ project, onStageClick, selectedStageIdx }) {
  const stageIdx = project.current_stage_index ?? 0
  const prob     = project.delay_probability ?? 0.5
  const stageData = STAGES.map((s, i) => {
    let risk
    if (i < stageIdx)      risk = Math.max(5,  Math.round(prob * 30 * (1 - i * 0.1)))
    else if (i === stageIdx) risk = Math.round(prob * 100)
    else                   risk = Math.round(prob * 100 * Math.exp(-(i - stageIdx) * 0.4) * 0.7)
    return { stage: s.replace(' ', '\n').replace(' ', '\n'), risk: Math.max(0, Math.min(risk, 100)), current: i === stageIdx, completed: i < stageIdx }
  })
  const barColor = e => e.completed ? '#94a3b8' : e.current ? (e.risk >= 70 ? 'var(--danger)' : e.risk >= 40 ? 'var(--warning)' : 'var(--success)') : '#cbd5e1'

  return (
    <div>
      {/* Dots */}
      <div style={{ display:'flex', alignItems:'center', marginBottom:20, overflowX:'auto', paddingBottom:4 }}>
        {STAGES.map((s, i) => {
          const done = i < stageIdx, cur = i === stageIdx
          const isSelected = selectedStageIdx === i
          return (
            <div key={i} style={{ display:'flex', alignItems:'center', flexShrink:0 }}>
              <div
                style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:4, cursor: onStageClick ? 'pointer' : 'default' }}
                onClick={() => onStageClick && onStageClick(i, s)}
                title={`Click for AI analysis: ${s}`}
              >
                <div style={{
                  width:28, height:28, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center',
                  fontWeight:700, fontSize:11,
                  background: isSelected ? '#7c3aed' : done ? 'var(--success)' : cur ? 'var(--primary)' : 'var(--gray-200)',
                  color: done || cur || isSelected ? '#fff' : 'var(--gray-400)',
                  boxShadow: isSelected ? '0 0 0 3px #ede9fe' : cur ? '0 0 0 3px var(--primary-light)' : 'none',
                  transition: 'all .15s',
                }}>
                  {done ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20,6 9,17 4,12"/></svg> : i+1}
                </div>
                <div style={{
                  fontSize:9, textAlign:'center', maxWidth:56, lineHeight:1.3,
                  color: isSelected ? '#7c3aed' : cur ? 'var(--primary)' : done ? 'var(--success)' : 'var(--gray-400)',
                  fontWeight: isSelected || cur ? 700 : 500,
                }}>{s.replace(' ','\n')}</div>
              </div>
              {i < STAGES.length-1 && <div style={{ width:28, height:2, margin:'0 4px', marginBottom:20, background: i<stageIdx?'var(--success)':'var(--gray-200)' }} />}
            </div>
          )
        })}
      </div>
      {onStageClick && (
        <div style={{ fontSize:10, color:'var(--gray-400)', marginBottom:8, textAlign:'center' }}>
          Click any stage dot for AI analysis ↑
        </div>
      )}
      {/* Bar chart */}
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={stageData} margin={{ top:4, right:8, bottom:20, left:0 }}
          onClick={(data, index) => { if (onStageClick && data?.activeTooltipIndex != null) onStageClick(data.activeTooltipIndex, STAGES[data.activeTooltipIndex]) }}>
          <XAxis dataKey="stage" tick={{ fontSize:8 }} interval={0} axisLine={false} tickLine={false} height={36} />
          <YAxis domain={[0,100]} tick={{ fontSize:10 }} tickFormatter={v=>`${v}%`} axisLine={false} tickLine={false} width={32} />
          <Tooltip formatter={(v) => [`${v}%`, 'Delay Risk']} />
          <Bar dataKey="risk" radius={[3,3,0,0]} maxBarSize={40} style={{ cursor: onStageClick ? 'pointer' : 'default' }}>
            {stageData.map((e,i) => (
              <Cell key={i} fill={selectedStageIdx===i ? '#7c3aed' : barColor(e)} opacity={e.completed?0.5:1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── Risk History Chart ───────────────────────────────────────────────────────
function RiskHistoryChart({ history }) {
  if (!history?.length) return (
    <div className="empty-state" style={{ padding: 24 }}>
      <div style={{ fontSize: 12, color: 'var(--gray-400)' }}>No history yet — re-score the project to start tracking.</div>
    </div>
  )

  const data = history.map(h => ({
    date:  new Date(h.scored_at).toLocaleDateString('en-IN', { day:'2-digit', month:'short' }),
    score: h.risk_score,
    prob:  Math.round(h.delay_probability * 100),
    trigger: h.trigger,
  }))

  const CustomDot = (props) => {
    const { cx, cy, payload } = props
    const c = payload.score >= 70 ? 'var(--danger)' : payload.score >= 40 ? 'var(--warning)' : 'var(--success)'
    return <circle cx={cx} cy={cy} r={5} fill={c} stroke="#fff" strokeWidth={2} />
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div style={{ background:'#fff', border:'1px solid var(--gray-200)', borderRadius:6, padding:'8px 12px', fontSize:11 }}>
        <div style={{ fontWeight:600, marginBottom:4 }}>{label}</div>
        <div>Risk Score: <strong style={{ color: d.score>=70?'var(--danger)':d.score>=40?'var(--warning)':'var(--success)' }}>{d.score}</strong></div>
        <div>Delay Prob: <strong>{d.prob}%</strong></div>
        <div style={{ color:'var(--gray-400)', marginTop:2 }}>Trigger: {d.trigger}</div>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top:8, right:16, bottom:8, left:0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
        <XAxis dataKey="date" tick={{ fontSize:10 }} axisLine={false} tickLine={false} />
        <YAxis domain={[0,100]} tick={{ fontSize:10 }} axisLine={false} tickLine={false} width={32} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={70} stroke="var(--danger)" strokeDasharray="4 2" strokeWidth={1} label={{ value:'High', fontSize:9, fill:'var(--danger)', position:'right' }} />
        <ReferenceLine y={40} stroke="var(--warning)" strokeDasharray="4 2" strokeWidth={1} label={{ value:'Med', fontSize:9, fill:'var(--warning)', position:'right' }} />
        <Line type="monotone" dataKey="score" stroke="var(--primary)" strokeWidth={2} dot={<CustomDot />} activeDot={{ r:7 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ─── Similar Projects Panel ───────────────────────────────────────────────────
function SimilarProjects({ projectId, navigate }) {
  const [similar, setSimilar] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSimilarProjects(projectId, 5)
      .then(r => setSimilar(r.data))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="spinner-wrap" style={{ padding:16 }}><div className="spinner" /></div>
  if (!similar.length) return <div style={{ fontSize:12, color:'var(--gray-400)', padding:8 }}>No similar projects found.</div>

  return (
    <div>
      {similar.map(p => (
        <div key={p.project_id}
          onClick={() => navigate(`/projects/${p.project_id}`)}
          style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'10px 0', borderBottom:'1px solid var(--gray-100)', cursor:'pointer' }}
          onMouseEnter={e => e.currentTarget.style.background='var(--gray-50)'}
          onMouseLeave={e => e.currentTarget.style.background='transparent'}>
          <div>
            <div style={{ fontSize:12, fontWeight:600, color:'var(--gray-800)' }}>{p.project_name}</div>
            <div style={{ fontSize:11, color:'var(--gray-500)' }}>{p.project_type} · {p.state}</div>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:10, flexShrink:0 }}>
            <div className="progress-wrap" style={{ width:48 }}>
              <div className="progress-bar" style={{ width:`${p.risk_score||0}%`, background: (p.risk_score||0)>=70?'var(--danger)':(p.risk_score||0)>=40?'var(--warning)':'var(--success)' }} />
            </div>
            <span style={{ fontSize:12, fontWeight:700, minWidth:26, textAlign:'right' }}>{p.risk_score}</span>
            <span style={{ fontSize:10, color:'var(--gray-400)', minWidth:36 }}>sim {Math.round(p.similarity_score*100)}%</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Actions Panel ────────────────────────────────────────────────────────────
function ActionsPanel({ projectId, currentUser }) {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', rule_id: '', officer_decision: 'accept', priority: 'medium', description: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    getProjectActions(projectId).then(r => setActions(r.data)).finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => { load() }, [load])

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await createAction(projectId, form)
      setForm({ title:'', rule_id:'', officer_decision:'accept', priority:'medium', description:'' })
      setShowForm(false)
      load()
    } catch(err) {
      alert('Error: ' + (err.response?.data?.detail || err.message))
    } finally { setSaving(false) }
  }

  async function handleStatus(id, status) {
    await updateAction(id, { status })
    load()
  }

  if (loading) return <div className="spinner-wrap" style={{ padding:16 }}><div className="spinner" /></div>

  return (
    <div>
      {/* Action list */}
      {actions.length === 0 && !showForm && (
        <div style={{ fontSize:12, color:'var(--gray-400)', padding:'8px 0', marginBottom:12 }}>No actions yet — assign one from the recommendations above.</div>
      )}
      {actions.map(a => (
        <div key={a.id} style={{
          padding:'10px 12px', borderRadius:'var(--radius)', marginBottom:8,
          border:`1px solid var(--gray-200)`,
          borderLeft:`3px solid ${STATUS_COLOR[a.status]||'var(--gray-300)'}`,
          background: a.status==='completed' ? 'var(--gray-50)' : '#fff',
        }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:8 }}>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
                {a.rule_id && <span style={{ fontSize:9, fontFamily:'var(--font-mono)', fontWeight:700, background:'var(--primary-light)', color:'var(--primary)', padding:'1px 5px', borderRadius:3 }}>{a.rule_id}</span>}
                <span style={{ fontSize:12, fontWeight:600, color:'var(--gray-800)' }}>{a.title}</span>
              </div>
              <div style={{ display:'flex', gap:10, fontSize:11, color:'var(--gray-500)', flexWrap:'wrap' }}>
                <span style={{ color: STATUS_COLOR[a.status], fontWeight:600 }}>{a.status.replace('_',' ')}</span>
                <span style={{ color: PRIORITY_COLOR[a.priority] }}>{a.priority} priority</span>
                {a.assigned_to_name && <span>Assigned: {a.assigned_to_name}</span>}
                {a.due_date && <span>Due: {new Date(a.due_date).toLocaleDateString('en-IN')}</span>}
                <span style={{ color:'var(--gray-400)' }}>{a.officer_decision}</span>
              </div>
              {a.description && <div style={{ fontSize:11, color:'var(--gray-500)', marginTop:4 }}>{a.description}</div>}
              {a.completion_note && <div style={{ fontSize:11, color:'var(--success)', marginTop:4 }}>✓ {a.completion_note}</div>}
            </div>
            {a.status !== 'completed' && a.status !== 'overridden' && (
              <div style={{ display:'flex', gap:6, flexShrink:0 }}>
                {a.status === 'open' && (
                  <button className="btn btn-outline btn-xs" onClick={() => handleStatus(a.id, 'in_progress')}>Start</button>
                )}
                <button className="btn btn-primary btn-xs" onClick={() => handleStatus(a.id, 'completed')}>
                  <Icon.Check /> Done
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Create action form */}
      {showForm ? (
        <form onSubmit={handleCreate} style={{ background:'var(--gray-50)', border:'1px solid var(--gray-200)', borderRadius:'var(--radius-lg)', padding:14, marginTop:8 }}>
          <div style={{ fontSize:12, fontWeight:700, color:'var(--gray-700)', marginBottom:10 }}>New Action Item — Officer Review</div>
          <div className="detail-grid" style={{ gridTemplateColumns:'1fr 1fr', gap:10, marginBottom:10 }}>
            <div style={{ gridColumn:'1/-1' }}>
              <label className="field-label">Action Title *</label>
              <input className="field-input" required placeholder="e.g. Release pending compensation payments"
                value={form.title} onChange={e => setForm(f=>({...f,title:e.target.value}))} />
            </div>
            <div>
              <label className="field-label">Related Rule</label>
              <select className="field-input" value={form.rule_id} onChange={e => setForm(f=>({...f,rule_id:e.target.value}))}>
                <option value="">None</option>
                {['R-01','R-02','R-03','R-04','R-05','R-06','R-07','R-08'].map(r=><option key={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">Priority</label>
              <select className="field-input" value={form.priority} onChange={e => setForm(f=>({...f,priority:e.target.value}))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="field-label">Officer Decision</label>
              <select className="field-input" value={form.officer_decision} onChange={e => setForm(f=>({...f,officer_decision:e.target.value}))}>
                <option value="accept">Accept Recommendation</option>
                <option value="modify">Modify</option>
                <option value="override">Override</option>
              </select>
            </div>
            <div style={{ gridColumn:'1/-1' }}>
              <label className="field-label">Description (optional)</label>
              <input className="field-input" placeholder="Additional context or modified instruction"
                value={form.description} onChange={e => setForm(f=>({...f,description:e.target.value}))} />
            </div>
          </div>
          <div style={{ display:'flex', gap:8 }}>
            <button className="btn btn-primary btn-sm" type="submit" disabled={saving}>{saving?'Saving…':'Assign Action'}</button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={()=>setShowForm(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button className="btn btn-outline btn-sm" style={{ marginTop:8, width:'100%', justifyContent:'center' }} onClick={()=>setShowForm(true)}>
          + Assign Action
        </button>
      )}
    </div>
  )
}

// ─── Edit Modal ───────────────────────────────────────────────────────────────
function EditModal({ project, onClose, onSaved }) {
  const [form, setForm] = useState({
    current_stage:             project.current_stage || '',
    days_in_current_stage:     project.days_in_current_stage ?? 0,
    days_since_last_action:    project.days_since_last_action ?? 0,
    compensation_pct:          project.compensation_pct ?? 0,
    compensation_pending_months: project.compensation_pending_months ?? 0,
    rr_completion_pct:         project.rr_completion_pct ?? 0,
    possession_pct:            project.possession_pct ?? 0,
    documentation_pct:         project.documentation_pct ?? 75,
    stakeholder_response_pct:  project.stakeholder_response_pct ?? 75,
    has_legal_dispute:         project.has_legal_dispute ?? false,
    num_legal_cases:           project.num_legal_cases ?? 0,
    ownership_conflicts:       project.ownership_conflicts ?? 0,
    pending_approvals:         project.pending_approvals ?? 0,
    noc_pending_count:         project.noc_pending_count ?? 0,
    budget_released:           project.budget_released ?? true,
    officer_responsiveness:    project.officer_responsiveness ?? 5,
    amount_paid_cr:            project.amount_paid_cr ?? 0,
    is_delayed:                project.is_delayed ?? false,
  })
  const [saving, setSaving] = useState(false)

  function set(e) {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : (type === 'number' ? parseFloat(value) || 0 : value) }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const r = await updateProject(project.project_id, form)
      onSaved(r.data)
    } catch(err) {
      alert('Save failed: ' + (err.response?.data?.detail || err.message))
    } finally { setSaving(false) }
  }

  const Section = ({ title, children }) => (
    <div style={{ marginBottom:20 }}>
      <div className="detail-section-title">{title}</div>
      <div className="detail-grid" style={{ gap:'10px 16px' }}>{children}</div>
    </div>
  )

  const F = ({ label, name, type='number', min, max, step='1', options, hint }) => (
    <div>
      <label className="field-label">{label}{hint&&<span style={{fontSize:9,color:'var(--gray-400)',marginLeft:4}}>{hint}</span>}</label>
      {options
        ? <select className="field-input" name={name} value={String(form[name])} onChange={e=>setForm(f=>({...f,[name]: e.target.value==='true'?true:e.target.value==='false'?false:e.target.value}))}>{options.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
        : type==='checkbox'
          ? <div style={{display:'flex',alignItems:'center',gap:8,marginTop:6}}><input type="checkbox" name={name} checked={!!form[name]} onChange={set} style={{width:16,height:16,cursor:'pointer'}} /><span style={{fontSize:12,color:'var(--gray-600)'}}>{form[name]?'Yes':'No'}</span></div>
          : <input className="field-input" type={type} name={name} value={form[name]} onChange={set} min={min} max={max} step={step} />
      }
    </div>
  )

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,.5)', zIndex:500, display:'flex', alignItems:'center', justifyContent:'center', padding:24 }} onClick={e=>e.target===e.currentTarget&&onClose()}>
      <div style={{ background:'#fff', borderRadius:12, width:'100%', maxWidth:720, maxHeight:'90vh', overflow:'auto', boxShadow:'0 20px 60px rgba(0,0,0,.2)' }}>
        <div style={{ padding:'20px 24px', borderBottom:'1px solid var(--gray-200)', display:'flex', justifyContent:'space-between', alignItems:'center', position:'sticky', top:0, background:'#fff', zIndex:1 }}>
          <div>
            <div style={{ fontSize:15, fontWeight:700 }}>Update Project Details</div>
            <div style={{ fontSize:12, color:'var(--gray-500)' }}>Changes will trigger automatic re-analysis</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><Icon.X /></button>
        </div>
        <form onSubmit={handleSave} style={{ padding:24 }}>
          <Section title="Acquisition Progress">
            <F label="Current Stage" name="current_stage" options={STAGES.map(s=>[s,s])} />
            <F label="Days in Stage" name="days_in_current_stage" min={0} />
            <F label="Days Since Last Action" name="days_since_last_action" min={0} hint="R-08" />
            <F label="Pending Approvals" name="pending_approvals" min={0} />
            <F label="NOC Pending" name="noc_pending_count" min={0} />
            <F label="Budget Released" name="budget_released" options={[['true','Yes'],['false','No']]} />
          </Section>
          <Section title="Compensation & R&R">
            <F label="Compensation %" name="compensation_pct" min={0} max={100} step="0.1" hint="R-01 <50%" />
            <F label="Months Pending" name="compensation_pending_months" min={0} />
            <F label="R&R Completion %" name="rr_completion_pct" min={0} max={100} step="0.1" hint="R-02 <50%" />
            <F label="Possession %" name="possession_pct" min={0} max={100} step="0.1" hint="R-07" />
            <F label="Documentation %" name="documentation_pct" min={0} max={100} step="0.1" hint="R-04 <60%" />
            <F label="Stakeholder Response %" name="stakeholder_response_pct" min={0} max={100} step="0.1" hint="R-05 <50%" />
            <F label="Amount Paid (Cr)" name="amount_paid_cr" min={0} step="0.01" />
          </Section>
          <Section title="Legal (R-03)">
            <F label="Legal Dispute" name="has_legal_dispute" type="checkbox" />
            <F label="Legal Cases" name="num_legal_cases" min={0} />
            <F label="Ownership Conflicts" name="ownership_conflicts" min={0} />
          </Section>
          <Section title="Governance (R-08)">
            <F label="Officer Responsiveness (1–10)" name="officer_responsiveness" min={1} max={10} step="0.1" />
            <F label="Confirmed Delayed" name="is_delayed" options={[['false','No'],['true','Yes']]} />
          </Section>
          <div style={{ display:'flex', gap:10, justifyContent:'flex-end' }}>
            <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              <Icon.Refresh />{saving ? 'Saving & Re-analyzing…' : 'Save & Re-analyze'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
const TABS = [
  { key:'overview',     label:'Overview'         },
  { key:'explanation',  label:'AI Explanation'   },
  { key:'history',      label:'Risk History'     },
  { key:'actions',      label:'Actions'          },
  { key:'similar',      label:'Similar Projects' },
]

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProjectDetailPage() {
  const { id }     = useParams()
  const navigate   = useNavigate()

  const [project,  setProject]  = useState(null)
  const [history,  setHistory]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [scoring,  setScoring]  = useState(false)
  const [tab,      setTab]      = useState('overview')
  const [showEdit, setShowEdit] = useState(false)
  const [explanation,      setExplanation]      = useState(null)
  const [explaining,       setExplaining]       = useState(false)
  const [stageExplanation, setStageExplanation] = useState(null)
  const [explainingStage,  setExplainingStage]  = useState(false)
  const [overallExpl,      setOverallExpl]      = useState(null)
  const [explainingOverall,setExplainingOverall]= useState(false)
  const [stageData,        setStageData]        = useState(null)
  // API key for test mode — stored in localStorage so it persists across reloads
  const [apiKey,     setApiKey]     = useState(() => localStorage.getItem('openai_api_key') || '')
  const [showApiKey, setShowApiKey] = useState(false)
  const [apiKeyInput,setApiKeyInput]= useState(() => localStorage.getItem('openai_api_key') || '')
  const [aiProvider, setAiProvider] = useState(() => localStorage.getItem('ai_provider') || 'groq')
  const [loadingStage, setLoadingStage] = useState(false)

  // Stage click — in-place AI analysis
  const [selectedStageIdx,  setSelectedStageIdx]  = useState(null)
  const [selectedStageName, setSelectedStageName] = useState(null)
  const [stageAiResult,     setStageAiResult]     = useState({}) // {stageIdx: {text, model, loading, error}}

  // Chat state
  const [chatHistory,   setChatHistory]   = useState([])  // [{role, content}]
  const [chatInput,     setChatInput]     = useState('')
  const [chatLoading,   setChatLoading]   = useState(false)
  const [chatInitialized, setChatInitialized] = useState(false)

  const user = JSON.parse(localStorage.getItem('user') || '{}')

  const loadAll = useCallback(() => {
    Promise.all([
      getProject(id),
      getRiskHistory(id),
    ]).then(([pr, hr]) => {
      setProject(pr.data)
      setHistory(hr.data)
    }).finally(() => setLoading(false))
  }, [id])

  useEffect(() => { loadAll() }, [loadAll])

  async function handleScore() {
    setScoring(true)
    try {
      await scoreProject(id)
      loadAll()
    } catch(e) {
      alert('Scoring failed: ' + (e.response?.data?.detail || e.message))
    } finally { setScoring(false) }
  }

  function saveApiKey() {
    localStorage.setItem('openai_api_key', apiKeyInput)
    setApiKey(apiKeyInput)
    setShowApiKey(false)
  }

  function clearApiKey() {
    localStorage.removeItem('openai_api_key')
    setApiKey('')
    setApiKeyInput('')
    setShowApiKey(false)
  }

  function changeProvider(p) {
    localStorage.setItem('ai_provider', p)
    setAiProvider(p)
    // Reset chat so it reinitializes with new provider context
    setChatHistory([])
    setChatInitialized(false)
  }

  async function handleExplain() {
    setExplaining(true)
    setTab('explanation')
    try {
      const r = await getExplanation(id, apiKey || null, aiProvider)
      setExplanation(r.data)
    } catch(e) {
      setExplanation({ error: e.response?.data?.detail || e.message })
    } finally { setExplaining(false) }
  }

  async function handleStageWiseExplain() {
    setExplainingStage(true)
    try {
      const r = await getStageWiseExplanation(id, apiKey || null)
      setStageExplanation(r.data)
    } catch(e) {
      setStageExplanation({ error: e.response?.data?.detail || e.message })
    } finally { setExplainingStage(false) }
  }

  async function handleOverallExplain() {
    setExplainingOverall(true)
    try {
      const r = await getOverallExplanation(id, apiKey || null, aiProvider)
      setOverallExpl(r.data)
    } catch(e) {
      setOverallExpl({ error: e.response?.data?.detail || e.message })
    } finally { setExplainingOverall(false) }
  }

  // Stage dot/bar click — fetch AI analysis for that specific stage in-place
  async function handleStageClick(stageIdx, stageName) {
    setSelectedStageIdx(stageIdx)
    setSelectedStageName(stageName)
    // If already loaded, just show it
    if (stageAiResult[stageIdx]?.text) return
    setStageAiResult(prev => ({ ...prev, [stageIdx]: { loading: true } }))
    try {
      const r = await getStageWiseExplanation(id, apiKey || null, aiProvider)
      const stageRecs = r.data.stage_recommendations || []
      // Store all stages at once so future clicks are instant
      const mapped = {}
      stageRecs.forEach(s => {
        mapped[s.stage_index] = { text: s.text, model: s.model_used, relation: s.relation, loading: false }
      })
      setStageAiResult(mapped)
    } catch(e) {
      setStageAiResult(prev => ({ ...prev, [stageIdx]: { error: e.response?.data?.detail || e.message, loading: false } }))
    }
  }

  // Chat: initialize with project summary then open chat tab
  async function initChat() {
    if (chatInitialized) { setTab('explanation'); return }
    setChatLoading(true)
    setChatInitialized(true)
    setTab('explanation')
    const welcomeMsg = {
      role: 'assistant',
      content: `Namaste! I've read the full details of **${id}**.\n\n` +
        `Risk Score: **${project.risk_score ?? 'Not scored'}/100** (${project.risk_category ?? 'N/A'})\n` +
        `Current Stage: **${project.current_stage ?? 'Unknown'}**\n` +
        (project.rules_triggered?.length ? `Triggered Rules: ${project.rules_triggered.join(', ')}\n` : '') +
        `\nAsk me anything about this project — risks, recommendations, legal basis, or specific stages.`,
    }
    setChatHistory([welcomeMsg])
    setChatLoading(false)
  }

  async function sendChatMessage(msg) {
    if (!msg.trim()) return
    const userMsg = { role: 'user', content: msg }
    const newHistory = [...chatHistory, userMsg]
    setChatHistory(newHistory)
    setChatInput('')
    setChatLoading(true)
    try {
      // Send history excluding the welcome message (index 0 if it's the AI greeting)
      const historyToSend = newHistory.slice(chatHistory[0]?.role === 'assistant' && !chatInitialized ? 0 : 0)
      const r = await chatWithProject(id, msg, historyToSend.slice(0, -1), apiKey || null, aiProvider)
      setChatHistory(h => [...h, { role: 'assistant', content: r.data.reply }])
    } catch(e) {
      setChatHistory(h => [...h, { role: 'assistant', content: `Error: ${e.response?.data?.detail || e.message}` }])
    } finally { setChatLoading(false) }
  }

  async function handleStageWise() {
    setLoadingStage(true)
    try {
      const r = await getStageWisePrediction(id)
      setStageData(r.data)
    } catch(e) {
      console.error('Stage prediction failed:', e)
    } finally { setLoadingStage(false) }
  }

  if (loading) return <div className="spinner-wrap"><div className="spinner" /></div>
  if (!project) return <div className="empty-state"><div className="empty-state-text">Project not found.</div></div>

  const shap  = project.shap_factors    || []
  const recs  = project.recommendations || []
  const rules = project.rules_triggered || []
  const rc    = project.risk_category
  const riskColor = RISK_COLOR[rc] || 'var(--gray-500)'

  return (
    <>
      {/* Breadcrumb */}
      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:20, fontSize:13, color:'var(--gray-500)' }}>
        <button className="btn btn-ghost btn-sm" style={{ padding:'4px 8px' }} onClick={() => navigate(-1)}>
          <Icon.ChevronLeft /> Back
        </button>
        <span>/</span><span>Projects</span><span>/</span>
        <span style={{ color:'var(--gray-800)', fontWeight:500 }}>{project.project_id}</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:6 }}>
            <h1 className="page-title" style={{ margin:0 }}>{project.project_name}</h1>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--gray-400)', background:'var(--gray-100)', padding:'2px 8px', borderRadius:4 }}>{project.project_id}</span>
          </div>
          <div className="page-subtitle">{project.project_type} · {project.district}, {project.state}</div>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          <button className="btn btn-outline" onClick={() => setShowEdit(true)}>
            Edit Details
          </button>
          <button className="btn btn-outline" onClick={initChat} disabled={!project.risk_score}
            style={{ background: tab==='explanation' ? 'var(--primary-light)' : '' }}>
            💬 AI Chat
          </button>
          <button className="btn btn-primary" onClick={handleScore} disabled={scoring}>
            <Icon.Refresh />{scoring ? 'Scoring…' : 'Re-score'}
          </button>
        </div>
      </div>

      {/* Risk summary strip */}
      <div className="card" style={{ marginBottom:20, padding:'16px 24px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:32, flexWrap:'wrap' }}>
          {/* Score */}
          <div style={{ display:'flex', alignItems:'baseline', gap:8 }}>
            <span style={{ fontSize:44, fontWeight:800, lineHeight:1, color:riskColor }}>{project.risk_score ?? '—'}</span>
            <span style={{ fontSize:14, color:'var(--gray-400)' }}>/100</span>
            <RiskBadge cat={rc} />
          </div>
          {/* Delay probability */}
          <div style={{ borderLeft:'1px solid var(--gray-200)', paddingLeft:24 }}>
            <div className="detail-field-label">Delay Probability</div>
            <div style={{ fontSize:22, fontWeight:700, color:riskColor }}>{project.delay_probability != null ? `${(project.delay_probability*100).toFixed(1)}%` : '—'}</div>
          </div>
          {/* Expected delay */}
          {project.expected_delay_label && (
            <div style={{ borderLeft:'1px solid var(--gray-200)', paddingLeft:24 }}>
              <div className="detail-field-label">Expected Delay</div>
              <div style={{ fontSize:14, fontWeight:600, color:'var(--gray-800)' }}>{project.expected_delay_label}</div>
              {project.model_confidence && <div style={{ fontSize:11, color:'var(--gray-400)' }}>Confidence: {project.model_confidence}</div>}
            </div>
          )}
          {/* Rules triggered */}
          {rules.length > 0 && (
            <div style={{ borderLeft:'1px solid var(--gray-200)', paddingLeft:24 }}>
              <div className="detail-field-label" style={{ marginBottom:6 }}>Rules Triggered</div>
              <div style={{ display:'flex', flexWrap:'wrap' }}>
                {rules.map(r => <RuleBadge key={r} ruleId={r} />)}
              </div>
            </div>
          )}
          {/* Last scored */}
          {project.last_scored_at && (
            <div style={{ marginLeft:'auto', textAlign:'right' }}>
              <div className="detail-field-label">Last Scored</div>
              <div style={{ fontSize:12, color:'var(--gray-600)' }}>{new Date(project.last_scored_at).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}</div>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display:'flex', gap:0, borderBottom:'2px solid var(--gray-200)', marginBottom:20 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{ padding:'10px 20px', border:'none', background:'transparent', cursor:'pointer', fontSize:13, fontWeight: tab===t.key ? 700 : 500, color: tab===t.key ? 'var(--primary)' : 'var(--gray-500)', borderBottom: tab===t.key ? '2px solid var(--primary)' : '2px solid transparent', marginBottom:-2 }}>
            {t.label}
            {t.key==='history' && history.length>0 && (
              <span style={{ marginLeft:6, fontSize:10, background:'var(--primary-light)', color:'var(--primary)', borderRadius:999, padding:'1px 6px', fontWeight:700 }}>{history.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab: AI Explanation ── */}
      {tab === 'explanation' && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 300px', gap:20, alignItems:'start' }}>

          {/* ── Main chat area ── */}
          <div style={{ display:'flex', flexDirection:'column', gap:0 }}>

            {/* API Key Panel */}
            <div style={{ marginBottom:12, padding:'10px 16px', borderRadius:'var(--radius)', background: apiKey ? '#f0fdf4' : '#fefce8', border:`1px solid ${apiKey ? '#86efac' : '#fde047'}` }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:10 }}>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  <span>{apiKey ? '🔑' : '⚠️'}</span>
                  <div>
                    <div style={{ fontSize:12, fontWeight:700, color: apiKey ? '#166534' : '#854d0e' }}>
                      {apiKey ? 'API Key Set' : 'No API Key — Fallback Mode'}
                    </div>
                    <div style={{ fontSize:11, color: apiKey ? '#15803d' : '#a16207' }}>
                      {apiKey ? `sk-...${apiKey.slice(-6)} · Saved in browser`
                        : 'Set API key for full AI analysis. Works in fallback mode too.'}
                    </div>
                  </div>
                </div>
                <div style={{ display:'flex', gap:6, flexShrink:0, alignItems:'center' }}>
                  {/* Provider selector */}
                  <div style={{ display:'flex', gap:4 }}>
                    {[
                      { id:'groq',       label:'Groq',        hint:'Free · Llama 3.1 70B · Fast' },
                      { id:'openai',     label:'OpenAI',      hint:'GPT-4o-mini · Paid' },
                      { id:'openrouter', label:'OpenRouter',  hint:'Mistral 7B · Free' },
                    ].map(p => (
                      <button key={p.id} title={p.hint}
                        onClick={() => changeProvider(p.id)}
                        style={{
                          padding:'3px 8px', borderRadius:4, fontSize:10, fontWeight:700, cursor:'pointer', border:'none',
                          background: aiProvider === p.id ? 'var(--primary)' : 'var(--gray-200)',
                          color:      aiProvider === p.id ? '#fff' : 'var(--gray-500)',
                        }}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                  {apiKey && <button className="btn btn-outline btn-sm" style={{ fontSize:10 }} onClick={clearApiKey}>Clear</button>}
                  <button className="btn btn-outline btn-sm" style={{ fontSize:10 }} onClick={() => setShowApiKey(v => !v)}>
                    {showApiKey ? 'Cancel' : apiKey ? 'Change' : 'Set Key'}
                  </button>
                </div>
              </div>
              {/* Provider hint */}
              <div style={{ marginTop:6, fontSize:10, color:'var(--gray-500)' }}>
                {aiProvider === 'groq'       && '🟢 Groq — FREE · Llama 3.1 70B · Fast · console.groq.com → API Keys → Create'}
                {aiProvider === 'openai'     && '🔵 OpenAI GPT-4o-mini — platform.openai.com (paid, ~$0.01/1K tokens)'}
                {aiProvider === 'openrouter' && '🟣 OpenRouter — openrouter.ai → Free tier available → API Keys'}
              </div>
              {showApiKey && (
                <div style={{ marginTop:10, display:'flex', gap:8 }}>
                  <input type="password" className="form-input" style={{ flex:1, fontFamily:'var(--font-mono)', fontSize:12 }}
                    placeholder={aiProvider === 'groq' ? 'gsk_...' : aiProvider === 'openrouter' ? 'sk-or-...' : 'sk-proj-...'}
                    value={apiKeyInput}
                    onChange={e => setApiKeyInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && saveApiKey()} />
                  <button className="btn btn-primary btn-sm" onClick={saveApiKey} disabled={!apiKeyInput.trim()}>Save</button>
                </div>
              )}
            </div>

            {/* Terminal-style Chat window */}
            <div style={{ borderRadius:'var(--radius)', overflow:'hidden', border:'1px solid #1e293b', boxShadow:'0 4px 24px rgba(0,0,0,.18)' }}>

              {/* Terminal title bar */}
              <div style={{ background:'#1e293b', padding:'8px 14px', display:'flex', alignItems:'center', gap:8 }}>
                <span style={{ width:10, height:10, borderRadius:'50%', background:'#ef4444', display:'inline-block' }}/>
                <span style={{ width:10, height:10, borderRadius:'50%', background:'#f59e0b', display:'inline-block' }}/>
                <span style={{ width:10, height:10, borderRadius:'50%', background:'#22c55e', display:'inline-block' }}/>
                <span style={{ fontFamily:'var(--font-mono)', fontSize:11, color:'#94a3b8', marginLeft:8 }}>
                  bhoomi-ai — {project.project_id} — {aiProvider}
                </span>
                {chatHistory.length > 0 && (
                  <button onClick={() => { setChatHistory([]); setChatInitialized(false) }}
                    style={{ marginLeft:'auto', background:'none', border:'none', color:'#64748b', cursor:'pointer', fontSize:10, fontFamily:'var(--font-mono)' }}>
                    clear
                  </button>
                )}
              </div>

              {/* Terminal body */}
              <div style={{ background:'#0f172a', minHeight:420, maxHeight:500, overflowY:'auto', padding:'12px 16px', display:'flex', flexDirection:'column', gap:8, fontFamily:'var(--font-mono)', fontSize:12 }}>

                {/* System info on load */}
                <div style={{ color:'#475569', lineHeight:1.6 }}>
                  <div>{'>'} Project loaded: <span style={{ color:'#38bdf8' }}>{project.project_id}</span> — {project.project_name}</div>
                  <div>{'>'} Risk: <span style={{ color: project.risk_score >= 70 ? '#f87171' : project.risk_score >= 40 ? '#fb923c' : '#4ade80' }}>{project.risk_score ?? 'N/A'}/100 ({project.risk_category ?? 'unscored'})</span></div>
                  <div>{'>'} Stage: <span style={{ color:'#a78bfa' }}>{project.current_stage}</span></div>
                  <div>{'>'} Provider: <span style={{ color:'#34d399' }}>{aiProvider}</span> {apiKey ? '· key set ✓' : '· <span style="color:#fbbf24">no key — set above</span>'}</div>
                  <div style={{ color:'#1e3a5f', marginTop:4 }}>{'─'.repeat(48)}</div>
                </div>

                {chatHistory.length === 0 && !chatLoading && (
                  <div style={{ color:'#64748b', lineHeight:2 }}>
                    <div>Suggested queries:</div>
                    {[
                      'Why is this project high risk?',
                      'What should be the first action?',
                      'Explain legal issues in simple terms',
                      'How long will delays last?',
                      'What does R-01 mean for this project?',
                    ].map(q => (
                      <div key={q} style={{ cursor:'pointer', color:'#38bdf8' }}
                        onClick={() => sendChatMessage(q)}>
                        $ {q}
                      </div>
                    ))}
                  </div>
                )}

                {chatHistory.map((msg, i) => (
                  <div key={i}>
                    {msg.role === 'user' ? (
                      <div style={{ color:'#38bdf8' }}>$ {msg.content}</div>
                    ) : (
                      <div style={{ color:'#e2e8f0', lineHeight:1.7, whiteSpace:'pre-wrap', paddingLeft:2 }}>
                        {msg.content}
                      </div>
                    )}
                  </div>
                ))}

                {chatLoading && (
                  <div style={{ color:'#64748b', fontFamily:'var(--font-mono)' }}>
                    <span style={{ animation:'pulse 1s infinite' }}>▋</span>
                  </div>
                )}
              </div>

              {/* Input line */}
              <div style={{ background:'#0f172a', borderTop:'1px solid #1e293b', padding:'8px 12px', display:'flex', alignItems:'center', gap:8 }}>
                <span style={{ color:'#38bdf8', fontFamily:'var(--font-mono)', fontSize:12, flexShrink:0 }}>$</span>
                <input
                  style={{ flex:1, background:'transparent', border:'none', outline:'none', color:'#f1f5f9', fontFamily:'var(--font-mono)', fontSize:12 }}
                  placeholder="Ask anything about this project…"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !chatLoading) { e.preventDefault(); sendChatMessage(chatInput) } }}
                  disabled={chatLoading}
                  autoFocus
                />
                <button className="btn btn-primary" style={{ fontSize:11, padding:'4px 12px', flexShrink:0 }}
                  onClick={() => sendChatMessage(chatInput)}
                  disabled={chatLoading || !chatInput.trim()}>
                  Run
                </button>
              </div>
            </div>

            {/* Quick analysis buttons below chat */}
            <div style={{ marginTop:12, display:'flex', gap:8, flexWrap:'wrap' }}>
              <span style={{ fontSize:11, color:'var(--gray-400)', alignSelf:'center' }}>Quick analysis:</span>
              <button className="btn btn-outline btn-sm" style={{ fontSize:11 }} onClick={handleExplain} disabled={explaining || !project.risk_score}>
                {explaining ? '…' : '🔍 Risk Explanation'}
              </button>
              <button className="btn btn-outline btn-sm" style={{ fontSize:11 }} onClick={handleOverallExplain} disabled={explainingOverall || !project.risk_score}>
                {explainingOverall ? '…' : '📋 Overall Recs'}
              </button>
            </div>

            {/* Quick analysis results */}
            {(explaining || explanation || explainingOverall || overallExpl) && (
              <div style={{ marginTop:12, display:'flex', flexDirection:'column', gap:12 }}>
                {explaining && <LoadingCard text="Generating risk explanation…" />}
                {explanation?.error && <ErrorCard msg={explanation.error} />}
                {explanation && !explanation.error && !explaining && (
                  <div className="card">
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
                      <div className="detail-section-title" style={{ margin:0 }}>🔍 Risk Explanation</div>
                      <ModelBadge model={explanation.model_used} tokens={explanation.tokens_used} chunks={explanation.kb_chunks_used} />
                    </div>
                    {explanation.why      && <ExplainSection title="Why This Risk Score" color="var(--danger)"  text={explanation.why} />}
                    {explanation.actions  && <ExplainSection title="Recommended Actions"  color="var(--warning)" text={explanation.actions} />}
                    {explanation.legal_basis && <ExplainSection title="Legal Basis" color="var(--primary)" text={explanation.legal_basis} footer="LARR Act 2013 · CAG Audit Reports" />}
                  </div>
                )}
                {explainingOverall && <LoadingCard text="Generating overall recommendations…" />}
                {overallExpl?.error && <ErrorCard msg={overallExpl.error} />}
                {overallExpl && !overallExpl.error && !explainingOverall && (
                  <div className="card">
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:10 }}>
                      <div className="detail-section-title" style={{ margin:0 }}>📋 Overall Recommendations</div>
                      <ModelBadge model={overallExpl.model_used} tokens={overallExpl.tokens_used} />
                    </div>
                    {overallExpl.summary          && <ExplainSection title="Summary"          color="var(--primary)" text={overallExpl.summary} />}
                    {overallExpl.critical_actions && <ExplainSection title="Critical Actions"  color="var(--danger)"  text={overallExpl.critical_actions} />}
                    {overallExpl.bottlenecks      && <ExplainSection title="Bottlenecks"       color="var(--warning)" text={overallExpl.bottlenecks} />}
                    {overallExpl.outlook          && <ExplainSection title="Outlook"           color="var(--success)" text={overallExpl.outlook} />}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Right sidebar ── */}
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {/* Project quick stats */}
            <div className="card" style={{ padding:'14px 16px' }}>
              <div className="detail-section-title">Project Snapshot</div>
              <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
                {[
                  { label:'Risk Score', value:`${project.risk_score ?? '—'}/100`, color: project.risk_score >= 70 ? 'var(--danger)' : project.risk_score >= 40 ? 'var(--warning)' : 'var(--success)' },
                  { label:'Stage', value: project.current_stage },
                  { label:'Compensation', value:`${project.compensation_pct ?? '—'}%` },
                  { label:'R&R', value:`${project.rr_completion_pct ?? '—'}%` },
                  { label:'Legal Cases', value: project.num_legal_cases },
                  { label:'Days No Action', value:`${project.days_since_last_action ?? '—'}d` },
                ].map(f => (
                  <div key={f.label} style={{ display:'flex', justifyContent:'space-between', fontSize:12 }}>
                    <span style={{ color:'var(--gray-500)' }}>{f.label}</span>
                    <span style={{ fontWeight:700, color: f.color || 'var(--gray-800)' }}>{f.value ?? '—'}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Knowledge base sources */}
            <div className="card" style={{ padding:'14px 16px' }}>
              <div className="detail-section-title">Knowledge Base</div>
              {[
                { id:'LARR Act 2013', url:'https://www.indiacode.nic.in/' },
                { id:'CAG MP Report', url:'https://cag.gov.in/' },
                { id:'R-01 to R-08', url:'' },
                { id:'FM-01 to FM-14', url:'' },
                { id:'LIFE + ADMIN', url:'' },
              ].map(s => (
                <div key={s.id} style={{ display:'flex', justifyContent:'space-between', padding:'5px 0', borderBottom:'1px solid var(--gray-100)', fontSize:11 }}>
                  <span style={{ fontFamily:'var(--font-mono)', color:'var(--primary)', fontWeight:700 }}>{s.id}</span>
                  {s.url && <a href={s.url} target="_blank" rel="noreferrer" style={{ color:'var(--primary)', textDecoration:'none' }}>↗</a>}
                </div>
              ))}
              <div style={{ marginTop:8, fontSize:10, color:'var(--gray-400)' }}>72 KB chunks · 4 files</div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Overview ── */}
      {tab === 'overview' && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 360px', gap:20 }}>
          <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
            {/* Stage timeline + stage-wise ML */}
            <div className="card">
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
                <div className="detail-section-title" style={{ margin:0 }}>Lifecycle Stage Analysis</div>
                <button className="btn btn-outline btn-sm" onClick={handleStageWise} disabled={loadingStage}>
                  {loadingStage ? 'Running…' : 'Run Stage ML'}
                </button>
              </div>
              <StageTimeline project={project} onStageClick={handleStageClick} selectedStageIdx={selectedStageIdx} />

              {/* In-place stage AI analysis */}
              {selectedStageIdx !== null && (
                <div style={{ marginTop:16, borderRadius:'var(--radius)', border:'2px solid #7c3aed', overflow:'hidden' }}>
                  <div style={{ background:'#7c3aed', padding:'10px 16px', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <span style={{ fontSize:18 }}>🔍</span>
                      <span style={{ fontWeight:700, fontSize:13, color:'#fff' }}>
                        AI Analysis: {selectedStageName}
                      </span>
                      {stageAiResult[selectedStageIdx]?.relation && (
                        <span style={{ fontSize:10, background:'rgba(255,255,255,.2)', color:'#fff', padding:'1px 7px', borderRadius:3 }}>
                          {stageAiResult[selectedStageIdx].relation.toUpperCase()}
                        </span>
                      )}
                    </div>
                    <button onClick={() => setSelectedStageIdx(null)}
                      style={{ background:'none', border:'none', color:'rgba(255,255,255,.7)', cursor:'pointer', fontSize:18, lineHeight:1 }}>×</button>
                  </div>
                  <div style={{ padding:16, background:'#faf5ff' }}>
                    {stageAiResult[selectedStageIdx]?.loading && (
                      <div style={{ display:'flex', alignItems:'center', gap:10, color:'var(--gray-500)', fontSize:13 }}>
                        <div className="spinner" style={{ width:16, height:16 }} />
                        Fetching AI analysis for all stages…
                      </div>
                    )}
                    {stageAiResult[selectedStageIdx]?.error && (
                      <div style={{ color:'var(--danger)', fontSize:12 }}>{stageAiResult[selectedStageIdx].error}</div>
                    )}
                    {stageAiResult[selectedStageIdx]?.text && !stageAiResult[selectedStageIdx]?.loading && (
                      <>
                        <div style={{ fontSize:13, color:'var(--gray-700)', lineHeight:1.8, whiteSpace:'pre-wrap' }}>
                          {stageAiResult[selectedStageIdx].text}
                        </div>
                        <div style={{ marginTop:10, display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                          <ModelBadge model={stageAiResult[selectedStageIdx].model} />
                          <div style={{ display:'flex', gap:8 }}>
                            {STAGES.map((s, i) => (
                              <button key={i} onClick={() => { setSelectedStageIdx(i); setSelectedStageName(s) }}
                                style={{ width:22, height:22, borderRadius:'50%', border:'none', cursor:'pointer', fontSize:9, fontWeight:700,
                                  background: i === selectedStageIdx ? '#7c3aed' : stageAiResult[i] ? 'var(--success)' : 'var(--gray-200)',
                                  color: i === selectedStageIdx || stageAiResult[i] ? '#fff' : 'var(--gray-500)',
                                }} title={s}>{i+1}</button>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                    {!stageAiResult[selectedStageIdx] && (
                      <div style={{ display:'flex', alignItems:'center', gap:10, color:'var(--gray-500)', fontSize:13 }}>
                        <div className="spinner" style={{ width:16, height:16 }} />
                        Loading…
                      </div>
                    )}
                  </div>
                </div>
              )}

              {stageData && (
                <div style={{ marginTop:20 }}>
                  <div style={{ fontSize:11, fontWeight:700, textTransform:'uppercase', letterSpacing:'.06em', color:'var(--gray-500)', marginBottom:10 }}>
                    Dedicated Stage-Wise ML Predictions
                  </div>
                  {stageData.stage_predictions.map((s, i) => {
                    const isCurrent = s.stage_index === (project.current_stage_index ?? 0)
                    const barColor  = !s.risk_score ? 'var(--gray-200)'
                      : s.risk_score >= 70 ? 'var(--danger)'
                      : s.risk_score >= 40 ? 'var(--warning)'
                      : 'var(--success)'
                    return (
                      <div key={i} style={{
                        padding:'10px 12px', marginBottom:6, borderRadius:'var(--radius)',
                        background: isCurrent ? 'var(--primary-light)' : 'var(--gray-50)',
                        border: `1px solid ${isCurrent ? 'var(--primary)' : 'var(--gray-200)'}`,
                      }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', gap:12 }}>
                          <div style={{ display:'flex', alignItems:'center', gap:8, minWidth:220 }}>
                            <div style={{ width:20, height:20, borderRadius:'50%', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center',
                              background: isCurrent ? 'var(--primary)' : 'var(--gray-300)', color:'#fff', fontSize:9, fontWeight:700 }}>
                              {s.stage_index + 1}
                            </div>
                            <span style={{ fontSize:12, fontWeight: isCurrent ? 700 : 500, color: isCurrent ? 'var(--primary)' : 'var(--gray-700)' }}>
                              {s.stage_name}
                              {isCurrent && <span style={{ marginLeft:6, fontSize:9, background:'var(--primary)', color:'#fff', padding:'1px 5px', borderRadius:3 }}>CURRENT</span>}
                            </span>
                          </div>
                          {s.risk_score != null ? (
                            <div style={{ display:'flex', alignItems:'center', gap:10, flex:1 }}>
                              <div className="progress-wrap" style={{ flex:1, maxWidth:120 }}>
                                <div className="progress-bar" style={{ width:`${s.risk_score}%`, background:barColor }} />
                              </div>
                              <span style={{ fontSize:13, fontWeight:700, color:barColor, minWidth:34 }}>{s.risk_score}</span>
                              <span className={`risk-badge ${s.risk_category}`} style={{ fontSize:10 }}>
                                <span className={`risk-dot ${s.risk_category}`} />{s.risk_category}
                              </span>
                              <span style={{ fontSize:11, color:'var(--gray-500)', minWidth:48 }}>
                                {(s.delay_probability * 100).toFixed(0)}%
                              </span>
                            </div>
                          ) : (
                            <span style={{ fontSize:11, color:'var(--gray-400)' }}>Insufficient data</span>
                          )}
                        </div>
                        {s.corrective_action && s.risk_score >= 40 && (
                          <div style={{ marginTop:6, fontSize:11, color:'var(--gray-600)', paddingLeft:28 }}>
                            {s.corrective_action}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
            {/* SHAP */}
            {shap.length > 0 && (
              <div className="card">
                <div className="detail-section-title">Risk Factor Analysis (SHAP)</div>
                <ShapChart factors={shap} />
              </div>
            )}
            {/* Recommendations + action creation */}
            {recs.length > 0 && (
              <div className="card">
                <div className="detail-section-title">AI Recommendations</div>
                {recs.map((r, i) => (
                  <div key={i} className="rec-item" style={{ cursor:'default' }}>
                    <div className="rec-icon"><Icon.AlertTriangle /></div>
                    <div style={{ flex:1 }}>
                      <div className="rec-text">{r}</div>
                    </div>
                    <button className="btn btn-outline btn-xs" style={{ flexShrink:0 }}
                      onClick={() => { setTab('actions') }}>
                      Assign
                    </button>
                  </div>
                ))}
                <div style={{ fontSize:11, color:'var(--gray-400)', marginTop:8 }}>
                  Click "Assign" to create an officer action item for any recommendation.
                </div>
              </div>
            )}
            {/* Project details */}
            <div className="card">
              <div className="detail-section-title">Project Details</div>
              <div className="detail-grid">
                <Field label="Type"             value={project.project_type} />
                <Field label="State"            value={project.state} />
                <Field label="District"         value={project.district} />
                <Field label="Start Date"       value={project.start_date} />
                <Field label="Land Area"        value={project.land_area_ha ? `${project.land_area_ha.toLocaleString()} ha` : null} />
                <Field label="Families"         value={project.families_affected?.toLocaleString()} />
                <Field label="Current Stage"    value={project.current_stage} />
                <Field label="Days in Stage"    value={project.days_in_current_stage != null ? `${project.days_in_current_stage} d` : null}
                  highlight={project.days_in_current_stage > 365 ? 'var(--danger)' : undefined} />
                <Field label="Days No Action"   value={project.days_since_last_action != null ? `${project.days_since_last_action} d` : null}
                  highlight={project.days_since_last_action > 90 ? 'var(--danger)' : undefined} />
                <Field label="Days No Update"   value={project.days_since_update != null ? `${project.days_since_update} d` : null}
                  highlight={project.days_since_update > 90 ? 'var(--danger)' : undefined} />
                <Field label="Pending Approvals" value={project.pending_approvals}
                  highlight={project.pending_approvals > 4 ? 'var(--warning)' : undefined} />
                <Field label="NOC Pending"      value={project.noc_pending_count} />
              </div>
            </div>
          </div>

          <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <div className="card">
              <div className="detail-section-title">Compensation & R&R</div>
              <ProgressField label="Compensation (R-01)" value={project.compensation_pct} threshold={50} />
              <ProgressField label="R&R (R-02)"          value={project.rr_completion_pct} threshold={50} />
              <ProgressField label="Possession (R-07)"   value={project.possession_pct} threshold={50} />
              <ProgressField label="Documentation (R-04)" value={project.documentation_pct} threshold={60} />
              <ProgressField label="Stakeholder (R-05)"  value={project.stakeholder_response_pct} threshold={50} />
              <hr className="divider" />
              <div className="detail-grid" style={{ gridTemplateColumns:'1fr 1fr' }}>
                <Field label="Land Cost"     value={project.land_cost_cr ? `₹${project.land_cost_cr.toFixed(1)} Cr` : null} />
                <Field label="Paid"          value={project.amount_paid_cr ? `₹${project.amount_paid_cr.toFixed(1)} Cr` : null} />
                <Field label="Project Value" value={project.project_value_cr ? `₹${project.project_value_cr.toFixed(1)} Cr` : null} />
                <Field label="Budget"        value={project.budget_released===true?'Released':project.budget_released===false?'Not Released':null}
                  highlight={project.budget_released===false?'var(--danger)':undefined} />
              </div>
            </div>
            <div className="card">
              <div className="detail-section-title">Legal (R-03)</div>
              <div className="detail-grid" style={{ gridTemplateColumns:'1fr 1fr' }}>
                <Field label="Dispute" value={project.has_legal_dispute?'Active':'None'}
                  highlight={project.has_legal_dispute?'var(--danger)':'var(--success)'} />
                <Field label="Cases"   value={project.num_legal_cases}
                  highlight={project.num_legal_cases>=3?'var(--danger)':undefined} />
                <Field label="Ownership Conflicts" value={project.ownership_conflicts??0}
                  highlight={(project.ownership_conflicts??0)>=3?'var(--danger)':undefined} />
                <Field label="Award Overdue" value={project.award_overdue?'Yes':'No'}
                  highlight={project.award_overdue?'var(--danger)':undefined} />
              </div>
            </div>
            <div className="card">
              <div className="detail-section-title">Governance (R-08)</div>
              <div className="detail-grid" style={{ gridTemplateColumns:'1fr 1fr' }}>
                <Field label="Officer Score" value={project.officer_responsiveness?`${project.officer_responsiveness}/10`:null}
                  highlight={project.officer_responsiveness<4?'var(--danger)':undefined} />
                <Field label="District Delay Rate" value={project.district_historical_delay_rate?`${(project.district_historical_delay_rate*100).toFixed(0)}%`:null}
                  highlight={project.district_historical_delay_rate>0.65?'var(--warning)':undefined} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Risk History ── */}
      {tab === 'history' && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 320px', gap:20 }}>
          <div className="card">
            <div className="detail-section-title">Risk Score Over Time</div>
            <RiskHistoryChart history={history} />
            <hr className="divider" />
            <div style={{ marginTop:8 }}>
              {history.length === 0 && <div style={{ fontSize:12, color:'var(--gray-400)' }}>No snapshots yet.</div>}
              {history.map((h, i) => (
                <div key={h.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 0', borderBottom:'1px solid var(--gray-100)' }}>
                  <div>
                    <div style={{ fontSize:12, fontWeight:600, color:'var(--gray-800)' }}>
                      Score: <span style={{ color: h.risk_score>=70?'var(--danger)':h.risk_score>=40?'var(--warning)':'var(--success)' }}>{h.risk_score}</span>
                      <span className={`risk-badge ${h.risk_category}`} style={{ marginLeft:8, fontSize:10 }}>{h.risk_category}</span>
                    </div>
                    <div style={{ fontSize:11, color:'var(--gray-500)', marginTop:2 }}>
                      {new Date(h.scored_at).toLocaleString('en-IN')} · Trigger: <strong>{h.trigger}</strong>
                    </div>
                    {h.notes && <div style={{ fontSize:11, color:'var(--gray-400)', marginTop:1 }}>{h.notes}</div>}
                  </div>
                  <div style={{ textAlign:'right', fontSize:11 }}>
                    <div style={{ color:'var(--gray-500)' }}>Delay: {(h.delay_probability*100).toFixed(1)}%</div>
                    {h.rules_triggered?.length>0 && (
                      <div style={{ marginTop:2 }}>{h.rules_triggered.map(r=><span key={r} style={{ fontSize:9, fontFamily:'var(--font-mono)', fontWeight:700, background:'var(--danger-light)', color:'var(--danger)', padding:'1px 4px', borderRadius:2, marginRight:2 }}>{r}</span>)}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="detail-section-title">Alert Required?</div>
            {project.risk_category === 'High' ? (
              <div style={{ padding:'12px', background:'var(--danger-light)', border:'1px solid var(--danger-border)', borderRadius:'var(--radius)', marginBottom:12 }}>
                <div style={{ fontSize:12, fontWeight:700, color:'var(--danger)', marginBottom:4 }}>Alert Recommended</div>
                <div style={{ fontSize:12, color:'var(--gray-700)' }}>This project is High Risk. Notify the concerned officer and escalate to prioritize interventions.</div>
              </div>
            ) : (
              <div style={{ padding:'12px', background:'var(--success-light)', border:'1px solid var(--success-border)', borderRadius:'var(--radius)', marginBottom:12 }}>
                <div style={{ fontSize:12, fontWeight:700, color:'var(--success)', marginBottom:4 }}>No Immediate Alert</div>
                <div style={{ fontSize:12, color:'var(--gray-700)' }}>Risk is {project.risk_category}. Continue regular monitoring.</div>
              </div>
            )}
            <div style={{ fontSize:11, color:'var(--gray-500)', marginBottom:8 }}>History snapshots: <strong>{history.length}</strong></div>
            <div style={{ fontSize:11, color:'var(--gray-500)' }}>Snapshots are created automatically when you:</div>
            <ul style={{ fontSize:11, color:'var(--gray-500)', paddingLeft:16, lineHeight:1.8, marginTop:4 }}>
              <li>Click Re-score (manual)</li>
              <li>Edit and save project details (update)</li>
              <li>Complete an action item (action_completed)</li>
              <li>Run batch scoring (batch)</li>
            </ul>
          </div>
        </div>
      )}

      {/* ── Tab: Actions ── */}
      {tab === 'actions' && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 320px', gap:20 }}>
          <div className="card">
            <div className="detail-section-title">Action Items — Officer Review & Tracking</div>
            <ActionsPanel projectId={id} currentUser={user} />
          </div>
          <div className="card">
            <div className="detail-section-title">Flow Guide</div>
            {[
              ['Officer Review', 'Review AI recommendations and decide: Accept, Modify, or Override'],
              ['Assign Action',  'Create an action item assigned to the responsible officer'],
              ['Track Progress', 'Officer updates status: Open → In Progress → Completed'],
              ['Re-analyze',     'Completing an action automatically re-scores the project'],
              ['Risk History',   'Each re-analysis snapshot appears in the Risk History tab'],
            ].map(([step, desc]) => (
              <div key={step} style={{ display:'flex', gap:10, marginBottom:12 }}>
                <div style={{ width:6, height:6, borderRadius:'50%', background:'var(--primary)', marginTop:5, flexShrink:0 }} />
                <div>
                  <div style={{ fontSize:12, fontWeight:600, color:'var(--gray-800)' }}>{step}</div>
                  <div style={{ fontSize:11, color:'var(--gray-500)' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Tab: Similar Projects ── */}
      {tab === 'similar' && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
          <div className="card">
            <div className="detail-section-title">Similar Projects (by type, risk, stage)</div>
            <SimilarProjects projectId={id} navigate={navigate} />
          </div>
          <div className="card">
            <div className="detail-section-title">This Project vs Similar</div>
            <div className="detail-grid" style={{ gridTemplateColumns:'1fr 1fr', gap:'8px 16px' }}>
              <Field label="Type"         value={project.project_type} />
              <Field label="Risk Score"   value={project.risk_score} />
              <Field label="Stage"        value={project.current_stage} />
              <Field label="Delay Prob"   value={project.delay_probability != null ? `${(project.delay_probability*100).toFixed(1)}%` : null} />
              <Field label="Compensation" value={project.compensation_pct != null ? `${project.compensation_pct}%` : null} />
              <Field label="R&R"          value={project.rr_completion_pct != null ? `${project.rr_completion_pct}%` : null} />
            </div>
            <hr className="divider" />
            <div style={{ fontSize:11, color:'var(--gray-400)' }}>Similarity is computed from project type, risk category, acquisition stage, and proximity of key metrics (compensation, R&R, delay probability).</div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEdit && (
        <EditModal
          project={project}
          onClose={() => setShowEdit(false)}
          onSaved={updated => {
            setProject(updated)
            setShowEdit(false)
            loadAll()
          }}
        />
      )}
    </>
  )
}

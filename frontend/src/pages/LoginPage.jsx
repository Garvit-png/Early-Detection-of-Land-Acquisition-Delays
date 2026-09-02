import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/authStore'

export default function LoginPage() {
  const { signIn }  = useAuth()
  const navigate    = useNavigate()
  const [form, setForm]       = useState({ username: '', password: '' })
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signIn(form.username, form.password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--gray-50)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <div style={{
        width: '100%',
        maxWidth: 900,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        borderRadius: 14,
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,.14)',
      }}>

        {/* ── Left: branding panel ── */}
        <div style={{
          background: 'var(--primary)',
          padding: '48px 40px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* background circle decoration */}
          <div style={{
            position: 'absolute', width: 260, height: 260, borderRadius: '50%',
            background: 'rgba(255,255,255,.05)',
            bottom: -60, right: -60, pointerEvents: 'none',
          }} />

          {/* top: org header */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: 'rgba(255,255,255,.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.9)" strokeWidth="1.8">
                  <line x1="3" y1="22" x2="21" y2="22"/>
                  <line x1="6" y1="18" x2="6" y2="11"/>
                  <line x1="10" y1="18" x2="10" y2="11"/>
                  <line x1="14" y1="18" x2="14" y2="11"/>
                  <line x1="18" y1="18" x2="18" y2="11"/>
                  <polygon points="12,2 20,7 4,7"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,.5)', letterSpacing: '.08em', textTransform: 'uppercase' }}>
                  Government of India
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,.85)' }}>
                  Ministry of Rural Development
                </div>
              </div>
            </div>

            <div style={{ fontSize: 24, fontWeight: 800, color: '#fff', lineHeight: 1.25, marginBottom: 14 }}>
              Land Acquisition<br />Delay Predictor
            </div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.6)', lineHeight: 1.65, maxWidth: 300 }}>
              AI-powered early warning system for monitoring land acquisition projects and predicting delays before they occur.
            </div>
          </div>

          {/* middle: feature list */}
          <div style={{ margin: '32px 0' }}>
            {[
              'Real-time risk scoring for every project',
              'SHAP-based explainable AI analysis',
              'GIS map with district-level visibility',
              'Role-based access across Central, State & District',
            ].map((f, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12 }}>
                <div style={{
                  width: 18, height: 18, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                  background: 'rgba(255,255,255,.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.8)" strokeWidth="3">
                    <polyline points="20,6 9,17 4,12"/>
                  </svg>
                </div>
                <span style={{ fontSize: 12.5, color: 'rgba(255,255,255,.7)', lineHeight: 1.5 }}>{f}</span>
              </div>
            ))}
          </div>

          {/* bottom: badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            padding: '7px 12px',
            background: 'rgba(255,255,255,.1)',
            border: '1px solid rgba(255,255,255,.15)',
            borderRadius: 6,
            fontSize: 11.5, color: 'rgba(255,255,255,.7)', fontWeight: 500,
            alignSelf: 'flex-start',
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            Dept of Land Resources (DoLR) — SIH 2026
          </div>
        </div>

        {/* ── Right: form panel ── */}
        <div style={{
          background: '#fff',
          padding: '48px 40px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}>
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginBottom: 6 }}>
              Sign in
            </h2>
            <p style={{ fontSize: 13, color: 'var(--gray-500)' }}>
              Enter your credentials to access the system
            </p>
          </div>

          {error && (
            <div style={{
              padding: '10px 14px',
              background: 'var(--danger-light)',
              border: '1px solid var(--danger-border)',
              borderRadius: 'var(--radius)',
              color: 'var(--danger)',
              fontSize: 12.5,
              marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label className="field-label">Username</label>
              <input className="field-input" type="text" required autoFocus
                autoComplete="username" placeholder="Enter your username"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
            </div>
            <div className="field">
              <label className="field-label">Password</label>
              <input className="field-input" type="password" required
                autoComplete="current-password" placeholder="Enter your password"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <button className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '10px', fontSize: 14, marginTop: 4 }}
              type="submit" disabled={loading}>
              {loading ? 'Authenticating…' : 'Sign In'}
            </button>
          </form>

          {/* Demo credentials */}
          <div style={{
            marginTop: 24,
            padding: '14px 16px',
            background: 'var(--gray-50)',
            border: '1px solid var(--gray-200)',
            borderRadius: 'var(--radius-lg)',
          }}>
            <div style={{
              fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '.07em', color: 'var(--gray-400)', marginBottom: 10,
            }}>
              Demo Credentials — click to fill
            </div>
            {[
              ['admin',            'Admin@123',    'Central'],
              ['up_officer',       'State@123',    'State — UP'],
              ['lucknow_officer',  'District@123', 'District'],
            ].map(([u, p, r]) => (
              <div key={u}
                onClick={() => setForm({ username: u, password: p })}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '7px 10px', borderRadius: 'var(--radius)',
                  cursor: 'pointer', marginBottom: 4,
                  transition: 'background .12s',
                  border: '1px solid transparent',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--primary-light)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--gray-700)', fontWeight: 600 }}>{u}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--gray-400)' }}>{p}</span>
                <span style={{
                  fontSize: 10, fontWeight: 600, color: 'var(--primary)',
                  background: 'var(--primary-light)', padding: '2px 7px', borderRadius: 3,
                }}>{r}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

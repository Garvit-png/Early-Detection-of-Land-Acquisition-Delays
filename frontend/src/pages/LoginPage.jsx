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
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      fontFamily: 'var(--font)',
    }}>

      {/* ── Left panel — green branding ── */}
      <div style={{
        background: 'linear-gradient(145deg, #1a5c3a 0%, #0f3d27 60%, #0a2d1c 100%)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '48px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Decorative circles */}
        <div style={{
          position: 'absolute', width: 320, height: 320, borderRadius: '50%',
          background: 'rgba(255,255,255,.04)', top: -80, right: -80,
        }} />
        <div style={{
          position: 'absolute', width: 200, height: 200, borderRadius: '50%',
          background: 'rgba(255,255,255,.04)', bottom: 60, left: -60,
        }} />
        <div style={{
          position: 'absolute', width: 120, height: 120, borderRadius: '50%',
          background: 'rgba(34,197,94,.1)', bottom: 200, right: 60,
        }} />

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, position: 'relative' }}>
          <img src="/logo_bhoomi.png" alt="Logo"
            style={{ width: 44, height: 44, borderRadius: 10, objectFit: 'contain' }} />
          <div>
            <div style={{ color: '#fff', fontSize: 15, fontWeight: 700 }}>Bhoomi Nivaran</div>
            <div style={{ color: 'rgba(255,255,255,.5)', fontSize: 11 }}>Ministry of Rural Development</div>
          </div>
        </div>

        {/* Center content */}
        <div style={{ position: 'relative' }}>
          {/* Big icon */}
          <div style={{
            width: 72, height: 72, borderRadius: 20,
            background: 'rgba(255,255,255,.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 28,
          }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.9)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </div>

          <h1 style={{ color: '#fff', fontSize: 30, fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>
            Land Acquisition<br />Delay Predictor
          </h1>
          <p style={{ color: 'rgba(255,255,255,.6)', fontSize: 13.5, lineHeight: 1.7, maxWidth: 320 }}>
            AI-powered predictive analytics for early detection of delays in land acquisition projects across India.
          </p>

          {/* Stats row */}
          <div style={{ display: 'flex', gap: 20, marginTop: 36 }}>
            {[['5000+', 'Projects'], ['28', 'States'], ['92%', 'Accuracy']].map(([val, label]) => (
              <div key={label} style={{
                background: 'rgba(255,255,255,.08)',
                border: '1px solid rgba(255,255,255,.12)',
                borderRadius: 12, padding: '12px 16px', textAlign: 'center', flex: 1,
              }}>
                <div style={{ color: '#22c55e', fontSize: 18, fontWeight: 800 }}>{val}</div>
                <div style={{ color: 'rgba(255,255,255,.5)', fontSize: 11, marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '8px 14px',
          background: 'rgba(255,255,255,.07)',
          border: '1px solid rgba(255,255,255,.12)',
          borderRadius: 999, color: 'rgba(255,255,255,.6)', fontSize: 11.5,
          position: 'relative',
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
          DoLR — Government of India
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div style={{
        background: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 40px',
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>

          {/* Header */}
          <div style={{ marginBottom: 32 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: '#f0fdf4', border: '1px solid #bbf7d0',
              borderRadius: 999, padding: '4px 12px',
              fontSize: 11.5, fontWeight: 600, color: '#16a34a',
              marginBottom: 16,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              Secure Portal
            </div>
            <h2 style={{ fontSize: 26, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>
              Welcome back
            </h2>
            <p style={{ fontSize: 13, color: '#64748b' }}>
              Sign in to access your dashboard
            </p>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '10px 14px',
              background: '#fef2f2', border: '1px solid #fecaca',
              borderRadius: 10, color: '#dc2626',
              fontSize: 13, marginBottom: 20,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Username
              </label>
              <input
                type="text" required autoFocus
                autoComplete="username"
                placeholder="Enter your username"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                style={{
                  width: '100%', padding: '11px 14px',
                  border: '1.5px solid #e2e8f0',
                  borderRadius: 10, fontSize: 13.5,
                  color: '#0f172a', background: '#fff',
                  outline: 'none', transition: 'border-color .15s, box-shadow .15s',
                  boxSizing: 'border-box',
                }}
                onFocus={e => { e.target.style.borderColor = '#1a5c3a'; e.target.style.boxShadow = '0 0 0 3px rgba(26,92,58,.1)' }}
                onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = 'none' }}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Password
              </label>
              <input
                type="password" required
                autoComplete="current-password"
                placeholder="Enter your password"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                style={{
                  width: '100%', padding: '11px 14px',
                  border: '1.5px solid #e2e8f0',
                  borderRadius: 10, fontSize: 13.5,
                  color: '#0f172a', background: '#fff',
                  outline: 'none', transition: 'border-color .15s, box-shadow .15s',
                  boxSizing: 'border-box',
                }}
                onFocus={e => { e.target.style.borderColor = '#1a5c3a'; e.target.style.boxShadow = '0 0 0 3px rgba(26,92,58,.1)' }}
                onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = 'none' }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%', padding: '12px',
                background: loading ? '#6b9e7e' : '#1a5c3a',
                color: '#fff', border: 'none',
                borderRadius: 10, fontSize: 14, fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background .15s, transform .1s',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
              onMouseEnter={e => { if (!loading) e.target.style.background = '#154d30' }}
              onMouseLeave={e => { if (!loading) e.target.style.background = '#1a5c3a' }}
            >
              {loading ? (
                <>
                  <span style={{
                    width: 14, height: 14, border: '2px solid rgba(255,255,255,.3)',
                    borderTopColor: '#fff', borderRadius: '50%',
                    animation: 'spin .65s linear infinite', display: 'inline-block',
                  }} />
                  Authenticating…
                </>
              ) : 'Sign In →'}
            </button>
          </form>

          {/* Demo credentials */}
          <div style={{
            marginTop: 28,
            padding: '16px',
            background: '#fff',
            border: '1px solid #e2e8f0',
            borderRadius: 12,
          }}>
            <div style={{
              fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '.07em', color: '#94a3b8', marginBottom: 12,
            }}>
              Demo accounts — click to fill
            </div>
            {[
              ['admin',            'Admin@123',    'Central',  '#dcfce7', '#16a34a'],
              ['up_officer',       'State@123',    'State',    '#dbeafe', '#2563eb'],
              ['lucknow_officer',  'District@123', 'District', '#fef9c3', '#a16207'],
            ].map(([u, p, r, bg, color]) => (
              <div key={u}
                onClick={() => setForm({ username: u, password: p })}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 10px', borderRadius: 8,
                  cursor: 'pointer', marginBottom: 4,
                  transition: 'background .12s',
                  border: '1px solid transparent',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: 8,
                  background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 700, color, flexShrink: 0,
                }}>
                  {u[0].toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{u}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>{p}</div>
                </div>
                <span style={{
                  fontSize: 10, fontWeight: 600, color,
                  background: bg, padding: '2px 8px', borderRadius: 4,
                }}>{r}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

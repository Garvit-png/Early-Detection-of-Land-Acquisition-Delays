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
      backgroundImage: 'url("/highway_bhoomi.avif")',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute',
        top: 24,
        left: 24,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <img src="/logo_bhoomi.png" alt="Bhoomi Logo"
             style={{
               width: 80,
               height: 'auto',
               maxHeight: 90,
               borderRadius: 12,
               objectFit: 'contain',
               display: 'block',
             }} />
        <span style={{
          color: '#000',
          fontSize: 18,
          fontWeight: 600,
          letterSpacing: '0.2px',
        }}>
          Bhoomi Nivaran
        </span>
      </div>
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
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '32px',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '100%',
            height: '100%',
            borderRadius: 20,
            overflow: 'hidden',
            boxShadow: '0 8px 24px rgba(0,0,0,.15)',
          }}>
            <img src="/bhoomi_nivaran_signin.jpeg" alt="Nivaran Illustration"
                 style={{
                   width: '100%',
                   height: '100%',
                   objectFit: 'cover',
                   display: 'block',
                 }} />
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

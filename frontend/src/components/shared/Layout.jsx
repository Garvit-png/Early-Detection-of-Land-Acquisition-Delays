import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/authStore'
import { useEffect, useState } from 'react'
import { getUnreadCount } from '../../services/api'
import { Icon } from './Icons'

const NAV = [
  { to: '/dashboard', label: 'Dashboard',  Icon: Icon.Dashboard },
  { to: '/projects',  label: 'Projects',   Icon: Icon.Projects  },
  { to: '/map',       label: 'GIS Map',    Icon: Icon.Map       },
  { to: '/analytics', label: 'Analytics',  Icon: Icon.TrendUp   },
  { to: '/alerts',    label: 'Alerts',     Icon: Icon.Bell, showBadge: true },
]
const ADMIN_NAV = [
  { to: '/audit', label: 'Audit Logs', Icon: Icon.Audit },
]

const ROLE_LABELS = {
  central:  'Central — All India',
  state:    (user) => `State — ${user?.state}`,
  district: (user) => `District — ${user?.district}`,
}

export default function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    getUnreadCount().then(r => setUnread(r.data.count)).catch(() => {})
    const id = setInterval(() =>
      getUnreadCount().then(r => setUnread(r.data.count)).catch(() => {}),
    30000)
    return () => clearInterval(id)
  }, [])

  const roleLabel = typeof ROLE_LABELS[user?.role] === 'function'
    ? ROLE_LABELS[user?.role](user)
    : ROLE_LABELS[user?.role] ?? user?.role

  return (
    <div className="layout">
      <nav className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="6" fill="rgba(255,255,255,.15)"/>
              <path d="M6 22V14l8-6 8 6v8H6z" stroke="rgba(255,255,255,.9)" strokeWidth="1.5" fill="none"/>
              <rect x="11" y="16" width="6" height="6" fill="rgba(255,255,255,.6)"/>
            </svg>
            <div className="sidebar-brand-name">Land Acquisition<br />Delay Predictor</div>
          </div>
          <div className="sidebar-brand-sub">Ministry of Rural Development — DoLR</div>
        </div>

        {/* Navigation */}
        <div className="sidebar-nav">
          <div className="sidebar-divider">Navigation</div>
          {NAV.map(({ to, label, Icon: NavIcon, showBadge }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <NavIcon />
              <span>{label}</span>
              {showBadge && unread > 0 && (
                <span className="nav-badge">{unread}</span>
              )}
            </NavLink>
          ))}

          {user?.role === 'central' && (
            <>
              <div className="sidebar-divider" style={{ marginTop: 8 }}>Administration</div>
              {ADMIN_NAV.map(({ to, label, Icon: NavIcon }) => (
                <NavLink key={to} to={to}
                  className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
                  <NavIcon />
                  <span>{label}</span>
                </NavLink>
              ))}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ minWidth: 0 }}>
              <div className="sidebar-user-name">{user?.username}</div>
              <div className="sidebar-user-role">{roleLabel}</div>
            </div>
            <button
              onClick={() => { signOut(); navigate('/login') }}
              title="Sign Out"
              style={{
                flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: 28, height: 28,
                border: '1px solid rgba(255,255,255,.2)',
                borderRadius: 'var(--radius)',
                background: 'transparent',
                color: 'rgba(255,255,255,.6)',
                cursor: 'pointer',
                transition: 'background .15s, color .15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,.1)'; e.currentTarget.style.color = '#fff' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,.6)' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16,17 21,12 16,7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </nav>

      <div className="main-wrap">
        <header className="topbar">
          <div>
            <div className="topbar-title">Predictive Analytics — Land Acquisition</div>
          </div>
          <div className="topbar-right">
            <div className="topbar-role-tag">
              <span style={{
                display: 'inline-block', width: 7, height: 7,
                borderRadius: '50%', background: 'var(--accent)', flexShrink: 0
              }} />
              {roleLabel}
            </div>
          </div>
        </header>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

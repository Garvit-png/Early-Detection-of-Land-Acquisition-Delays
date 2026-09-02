import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/authStore'
import { useEffect, useState } from 'react'
import { getUnreadCount } from '../../services/api'

const NAV = [
  { to: '/dashboard', label: 'Dashboard',  icon: '📊' },
  { to: '/projects',  label: 'Projects',   icon: '📁' },
  { to: '/map',       label: 'GIS Map',    icon: '🗺️' },
  { to: '/alerts',    label: 'Alerts',     icon: '🔔' },
]
const ADMIN_NAV = [
  { to: '/audit', label: 'Audit Logs', icon: '📋' },
]

export default function Layout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    getUnreadCount().then(r => setUnread(r.data.count)).catch(() => {})
    const interval = setInterval(() => {
      getUnreadCount().then(r => setUnread(r.data.count)).catch(() => {})
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  function handleSignOut() {
    signOut()
    navigate('/login')
  }

  const roleLabel = { central: 'Central — All India', state: `State — ${user?.state}`, district: `District — ${user?.district}` }

  return (
    <div className="layout">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-logo">
          <h2>🏛️ Land Acquisition<br/>Delay Predictor</h2>
          <span>Ministry of Rural Development</span>
        </div>

        <div className="sidebar-nav">
          <div className="nav-section">Navigation</div>
          {NAV.map(n => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <span>{n.icon}</span>
              <span>{n.label}</span>
              {n.to === '/alerts' && unread > 0 && (
                <span className="bell-badge" style={{ position: 'static', marginLeft: 'auto' }}>{unread}</span>
              )}
            </NavLink>
          ))}

          {user?.role === 'central' && (
            <>
              <div className="nav-section" style={{ marginTop: 8 }}>Admin</div>
              {ADMIN_NAV.map(n => (
                <NavLink key={n.to} to={n.to}
                  className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
                  <span>{n.icon}</span>
                  <span>{n.label}</span>
                </NavLink>
              ))}
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <strong>{user?.username}</strong>
            <span>{roleLabel[user?.role]}</span>
          </div>
          <button className="btn btn-outline btn-sm" style={{ marginTop: 10, width: '100%', color: '#94a3b8', borderColor: '#334155' }}
            onClick={handleSignOut}>Sign Out</button>
        </div>
      </nav>

      {/* Main content */}
      <div className="main-wrap">
        <header className="topbar">
          <div className="topbar-title">DoLR — Predictive Analytics System</div>
          <div className="topbar-right">
            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>
              Role: <strong>{user?.role}</strong>
            </span>
          </div>
        </header>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

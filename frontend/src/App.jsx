import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthContext, useAuthProvider } from './store/authStore'
import Layout from './components/shared/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import MapPage from './pages/MapPage'
import AlertsPage from './pages/AlertsPage'
import AuditPage from './pages/AuditPage'

function RequireAuth({ children }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  const auth = useAuthProvider()

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"          element={<DashboardPage />} />
            <Route path="projects"           element={<ProjectsPage />} />
            <Route path="projects/:id"       element={<ProjectDetailPage />} />
            <Route path="map"                element={<MapPage />} />
            <Route path="alerts"             element={<AlertsPage />} />
            <Route path="audit"              element={<AuditPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

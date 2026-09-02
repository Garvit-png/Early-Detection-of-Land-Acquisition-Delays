import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import { getMapData } from '../services/api'

const RISK_COLORS = { High: '#dc2626', Medium: '#d97706', Low: '#16a34a' }
const RISK_RADIUS = { High: 9, Medium: 7, Low: 5 }

export default function MapPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [counts, setCounts] = useState({ High: 0, Medium: 0, Low: 0 })

  useEffect(() => {
    const params = {}
    if (filter) params.risk_category = filter
    setLoading(true)
    getMapData(params)
      .then(r => {
        setProjects(r.data)
        const c = { High: 0, Medium: 0, Low: 0 }
        r.data.forEach(p => { if (c[p.risk_category] !== undefined) c[p.risk_category]++ })
        setCounts(c)
      })
      .finally(() => setLoading(false))
  }, [filter])

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 className="page-title" style={{ margin: 0 }}>GIS Risk Map</h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Legend */}
          {['High', 'Medium', 'Low'].map(r => (
            <button key={r}
              className={`btn btn-sm ${filter === r ? 'btn-primary' : 'btn-outline'}`}
              style={{ gap: 6 }}
              onClick={() => setFilter(f => f === r ? '' : r)}>
              <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: RISK_COLORS[r] }} />
              {r} ({counts[r]})
            </button>
          ))}
          {filter && <button className="btn btn-outline btn-sm" onClick={() => setFilter('')}>Clear</button>}
        </div>
      </div>

      {loading && <div className="spinner" />}

      <div className="map-container">
        <MapContainer
          center={[22.5, 80.0]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {projects.map(p => (
            <CircleMarker
              key={p.id}
              center={[p.latitude, p.longitude]}
              radius={RISK_RADIUS[p.risk_category] || 6}
              pathOptions={{
                fillColor: RISK_COLORS[p.risk_category] || '#64748b',
                color: '#fff',
                weight: 1.5,
                fillOpacity: 0.85,
              }}
            >
              <Popup>
                <div style={{ minWidth: 200, fontFamily: 'sans-serif', fontSize: 13 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>{p.project_name}</div>
                  <div style={{ marginBottom: 4 }}>
                    <span style={{ background: RISK_COLORS[p.risk_category] || '#ccc', color: '#fff', padding: '1px 6px', borderRadius: 4, fontSize: 11 }}>
                      {p.risk_category} Risk
                    </span>
                    <span style={{ marginLeft: 6, fontWeight: 600 }}>{p.risk_score}/100</span>
                  </div>
                  <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>📍 {p.district}, {p.state}</div>
                  <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>🏗 {p.project_type}</div>
                  <div style={{ fontSize: 12, color: '#555', marginBottom: 8 }}>📋 {p.current_stage}</div>
                  <button
                    style={{ background: '#1e40af', color: '#fff', border: 'none', padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
                    onClick={() => navigate(`/projects/${p.project_id}`)}>
                    View Details →
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--gray-500)' }}>
        Showing {projects.length} projects with risk scores and coordinates. Click any marker for details.
      </div>
    </>
  )
}

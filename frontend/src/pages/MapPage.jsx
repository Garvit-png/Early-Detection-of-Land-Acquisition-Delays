import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import { getMapData } from '../services/api'

const RISK_CONFIG = {
  High:   { color: '#c0392b', radius: 9 },
  Medium: { color: '#b7770d', radius: 7 },
  Low:    { color: '#1a6b3a', radius: 5 },
}

export default function MapPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState('')
  const [counts, setCounts] = useState({ High: 0, Medium: 0, Low: 0 })

  useEffect(() => {
    const params = {}
    if (activeFilter) params.risk_category = activeFilter
    setLoading(true)
    getMapData(params)
      .then(r => {
        setProjects(r.data)
        const c = { High: 0, Medium: 0, Low: 0 }
        r.data.forEach(p => { if (c[p.risk_category] !== undefined) c[p.risk_category]++ })
        setCounts(c)
      })
      .finally(() => setLoading(false))
  }, [activeFilter])

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">GIS Risk Map</h1>
          <div className="page-subtitle">
            Geographical distribution of land acquisition projects by risk level
          </div>
        </div>
      </div>

      {/* Legend / filter bar */}
      <div className="card" style={{ marginBottom: 16, padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
            Filter by risk:
          </span>
          {['High', 'Medium', 'Low'].map(r => (
            <button
              key={r}
              className={`btn btn-sm ${activeFilter === r ? 'btn-primary' : 'btn-outline'}`}
              style={activeFilter === r ? {} : { borderColor: RISK_CONFIG[r].color + '60', color: 'var(--gray-700)' }}
              onClick={() => setActiveFilter(f => f === r ? '' : r)}>
              <span style={{
                display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                background: RISK_CONFIG[r].color, flexShrink: 0
              }} />
              {r} Risk ({counts[r].toLocaleString()})
            </button>
          ))}
          {activeFilter && (
            <button className="btn btn-ghost btn-sm" onClick={() => setActiveFilter('')}>
              Show All
            </button>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--gray-400)' }}>
            {loading ? 'Loading…' : `${projects.length.toLocaleString()} projects displayed`}
          </span>
        </div>
      </div>

      <div className="map-wrap">
        <MapContainer center={[22.5, 80.0]} zoom={5} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {projects.map(p => {
            const cfg = RISK_CONFIG[p.risk_category] || { color: '#9aa0ae', radius: 5 }
            return (
              <CircleMarker
                key={p.id}
                center={[p.latitude, p.longitude]}
                radius={cfg.radius}
                pathOptions={{
                  fillColor: cfg.color,
                  color: '#fff',
                  weight: 1.5,
                  fillOpacity: 0.82,
                }}>
                <Popup>
                  <div style={{ minWidth: 220, fontFamily: 'var(--font, sans-serif)', fontSize: 13, lineHeight: 1.5 }}>
                    <div style={{ fontWeight: 700, color: '#111', marginBottom: 8 }}>
                      {p.project_name}
                    </div>
                    <div style={{ marginBottom: 6 }}>
                      <span style={{
                        display: 'inline-block',
                        background: cfg.color,
                        color: '#fff',
                        padding: '2px 8px',
                        borderRadius: 3,
                        fontSize: 11,
                        fontWeight: 700,
                        marginRight: 6,
                      }}>
                        {p.risk_category} Risk
                      </span>
                      <span style={{ fontWeight: 700, color: cfg.color }}>
                        {p.risk_score}/100
                      </span>
                    </div>
                    <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                      <tbody>
                        {[
                          ['Location', `${p.district}, ${p.state}`],
                          ['Type', p.project_type],
                          ['Stage', p.current_stage],
                          ['Families', p.families_affected?.toLocaleString()],
                        ].map(([k, v]) => (
                          <tr key={k}>
                            <td style={{ color: '#888', paddingRight: 8, paddingBottom: 3, whiteSpace: 'nowrap' }}>{k}</td>
                            <td style={{ color: '#333', fontWeight: 500 }}>{v}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <button
                      style={{
                        marginTop: 10, width: '100%',
                        background: '#1a3c6e', color: '#fff',
                        border: 'none', padding: '6px 12px',
                        borderRadius: 4, cursor: 'pointer',
                        fontSize: 12, fontWeight: 600,
                      }}
                      onClick={() => navigate(`/projects/${p.project_id}`)}>
                      View Project Details
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </>
  )
}

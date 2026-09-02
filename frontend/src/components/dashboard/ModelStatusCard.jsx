import { useEffect, useState } from 'react'
import { getModelStatus, retrainModel } from '../../services/api'
import { useAuth } from '../../store/authStore'

export default function ModelStatusCard() {
  const { user } = useAuth()
  const [status, setStatus]     = useState(null)
  const [retraining, setRetrain] = useState(false)
  const [result, setResult]      = useState(null)

  useEffect(() => {
    getModelStatus().then(r => setStatus(r.data)).catch(() => {})
  }, [])

  async function handleRetrain() {
    setRetrain(true)
    setResult(null)
    try {
      const r = await retrainModel()
      setResult(r.data)
      setStatus(s => ({
        ...s,
        accuracy:    r.data.accuracy,
        roc_auc:     r.data.roc_auc,
        f1_score:    r.data.f1_score,
        train_rows:  r.data.train_rows,
        trained_at:  r.data.trained_at,
        data_source: r.data.data_source,
      }))
    } catch (e) {
      alert('Retraining failed: ' + (e.response?.data?.detail || e.message))
    } finally {
      setRetrain(false)
    }
  }

  const metricBar = (val, max = 1) => {
    const pct = Math.round((val / max) * 100)
    const color = pct >= 75 ? 'var(--success)' : pct >= 55 ? 'var(--warning)' : 'var(--danger)'
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, height: 5, background: 'var(--gray-100)', borderRadius: 99, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99 }} />
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--font-mono)', color, minWidth: 36 }}>
          {(val * 100).toFixed(1)}%
        </span>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <div className="card-title" style={{ marginBottom: 2 }}>AI Model Status</div>
          <div style={{ fontSize: 11, color: 'var(--gray-400)' }}>
            XGBoost + SHAP — {status?.feature_count || 23} features
          </div>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '3px 10px', borderRadius: 999,
          background: status?.loaded ? 'var(--success-light)' : 'var(--danger-light)',
          border: `1px solid ${status?.loaded ? 'var(--success-border)' : 'var(--danger-border)'}`,
          fontSize: 11, fontWeight: 700,
          color: status?.loaded ? 'var(--success)' : 'var(--danger)',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: status?.loaded ? 'var(--success)' : 'var(--danger)', display: 'inline-block' }} />
          {status?.loaded ? 'Loaded' : 'Not Loaded'}
        </div>
      </div>

      {/* Metrics */}
      {status?.roc_auc ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
          {[
            { label: 'ROC-AUC',  val: status.roc_auc  },
            { label: 'Accuracy', val: status.accuracy  },
            { label: 'F1 Score', val: status.f1_score  },
          ].map(({ label, val }) => (
            <div key={label}>
              <div style={{ fontSize: 11, color: 'var(--gray-500)', marginBottom: 3 }}>{label}</div>
              {metricBar(val)}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 16 }}>Metrics not available</div>
      )}

      {/* Meta */}
      {status?.trained_at && (
        <div style={{ fontSize: 11, color: 'var(--gray-400)', marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 3 }}>
          <div>Trained on: <strong style={{ color: 'var(--gray-600)' }}>{status.train_rows?.toLocaleString()} rows</strong></div>
          <div>Data source: <strong style={{ color: 'var(--gray-600)', textTransform: 'capitalize' }}>{status.data_source}</strong></div>
          <div>Last trained: <strong style={{ color: 'var(--gray-600)' }}>{new Date(status.trained_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })}</strong></div>
        </div>
      )}

      {/* Retrain result banner */}
      {result && (
        <div style={{ padding: '8px 12px', background: 'var(--success-light)', border: '1px solid var(--success-border)', borderRadius: 'var(--radius)', fontSize: 12, color: 'var(--success)', marginBottom: 12 }}>
          Model retrained on {result.train_rows.toLocaleString()} rows from {result.data_source}. ROC-AUC: {(result.roc_auc * 100).toFixed(1)}%
        </div>
      )}

      {/* Retrain button — central only */}
      {user?.role === 'central' && (
        <button
          className="btn btn-outline btn-sm"
          style={{ width: '100%', justifyContent: 'center' }}
          onClick={handleRetrain}
          disabled={retraining}>
          {retraining
            ? <><span className="spinner" style={{ width: 12, height: 12, borderWidth: 2, margin: 0 }} /> Retraining…</>
            : 'Retrain Model on New Data'
          }
        </button>
      )}
    </div>
  )
}

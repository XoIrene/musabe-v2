import { useEffect, useState } from 'react'
import { api, fmt } from '../api'
import { useAuth } from '../auth'

export default function WriteOffs() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [f, setF] = useState({ code: '', kind: 'LOST', reason: '' })
  const [err, setErr] = useState('')
  const load = () => api('/writeoffs/').then(setRows)
  useEffect(load, [])
  const report = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/writeoffs/', { method: 'POST', body: f }); setF({ code: '', kind: 'LOST', reason: '' }); load() } catch (e) { setErr(e.message) }
  }
  const decide = async (id, approve) => { await api(`/writeoffs/${id}/decide/`, { method: 'POST', body: { approve } }); load() }
  return (
    <>
      <h2>Write-offs</h2>
      {user.role === 'LIBRARIAN' && (
        <form className="card" onSubmit={report}>
          <h3>Report a lost or damaged book</h3>
          <div className="line">
            <input required placeholder="Book code" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} />
            <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}><option value="LOST">Lost</option><option value="DAMAGED">Damaged</option></select>
            <input required placeholder="What happened?" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} />
            <button className="primary">Send to Head Master</button>
          </div>
          {err && <p className="error">{err}</p>}
        </form>
      )}
      <section className="card">
        <table><thead><tr><th>Book</th><th>Kind</th><th>Reason</th><th>Reported</th><th>Status</th><th></th></tr></thead>
          <tbody>{rows.map((w) => (
            <tr key={w.id}><td><span className="mono">{w.code}</span> {w.item_name}</td><td>{w.kind}</td><td>{w.reason}</td>
              <td>{w.reported_by_name}<br /><span className="muted">{fmt(w.reported_at)}</span></td>
              <td><span className={'pill ' + w.status.toLowerCase()}>{w.status}</span>{w.decided_by_name && <div className="muted">{w.decided_by_name}</div>}</td>
              <td>{user.role === 'HEAD_MASTER' && w.status === 'PENDING' && <>
                <button className="primary" onClick={() => decide(w.id, true)}>Approve</button>{' '}
                <button className="danger" onClick={() => decide(w.id, false)}>Reject</button></>}</td></tr>))}</tbody></table>
        {rows.length === 0 && <p className="muted">No write-off reports.</p>}
      </section>
    </>
  )
}

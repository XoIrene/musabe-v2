import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, fmt, STATUS } from '../api'

export default function RequestDetail() {
  const { id } = useParams()
  const [r, setR] = useState(null)
  const [note, setNote] = useState('')
  const [supplier, setSupplier] = useState('')
  const [err, setErr] = useState('')
  const load = () => api(`/requests/${id}/`).then(setR)
  useEffect(() => { load() }, [id])

  const act = async (a) => {
    setErr('')
    try {
      setR(await api(`/requests/${id}/act/`, { method: 'POST', body: { action: a.action, note, supplier } }))
      setNote('')
    } catch (e) { setErr(e.message) }
  }
  if (!r) return <p>Loading…</p>
  const needNote = r.actions.some((a) => a.needs_note)
  const needSupplier = r.actions.some((a) => a.needs_supplier)
  return (
    <>
      <h2>#{r.id} · {r.title}</h2>
      <p><span className={'pill ' + r.status.toLowerCase()}>{STATUS[r.status]}</span>{' '}
        <span className="muted">{r.kind === 'BOOKS' ? 'Books (13 steps)' : 'Other items (9 steps)'} · {r.branch_name} · by {r.requestor_name}</span></p>
      <section className="card">
        <h3>Items</h3>
        <table><thead><tr><th>Item</th><th>Category</th><th>Qty</th></tr></thead>
          <tbody>{r.lines.map((l) => <tr key={l.id}><td>{l.name}{l.author && ` — ${l.author}`}{l.size && ` (${l.size})`}</td><td>{l.category}</td><td>{l.quantity}</td></tr>)}</tbody></table>
        {r.justification && <p className="muted">{r.justification}</p>}
        <p className="muted">{[r.requisition_no, r.po_number, r.supplier && 'Supplier: ' + r.supplier].filter(Boolean).join(' · ')}</p>
      </section>
      {r.actions.length > 0 && (
        <section className="card action">
          <h3>Your action</h3>
          {needSupplier && <label>Supplier<input value={supplier} onChange={(e) => setSupplier(e.target.value)} /></label>}
          {needNote && <label>Note (required to reject / report a problem)<input value={note} onChange={(e) => setNote(e.target.value)} /></label>}
          {err && <p className="error">{err}</p>}
          <div className="buttons">{r.actions.map((a) => (
            <button key={a.action} className={a.danger ? 'danger' : 'primary'} onClick={() => act(a)}>{a.label}</button>))}</div>
        </section>
      )}
      <section className="card">
        <h3>History</h3>
        <ol className="timeline">{r.steps.map((s) => (
          <li key={s.id}><b>{s.action.replace(/_/g, ' ')}</b> — {s.actor_name} <span className="muted">({s.actor_role})</span>
            <span className="muted"> · {fmt(s.created_at)}</span>{s.note && <div>“{s.note}”</div>}</li>))}</ol>
      </section>
    </>
  )
}

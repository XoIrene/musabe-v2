import { useEffect, useState } from 'react'
import { api, fmt } from '../api'
import { useAuth } from '../auth'

export default function Contributions() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [branches, setBranches] = useState([])
  const [f, setF] = useState({ branch: '', name: '', quantity: 1, parent_name: '' })
  const [err, setErr] = useState('')
  const load = () => api('/contributions/').then(setRows)
  useEffect(() => {
    load()
    api('/branches/').then((b) => {
      const mine = b.filter((x) => x.type === 'PRIMARY' && user.branches.includes(x.id)); setBranches(mine)
      if (mine[0]) setF((p) => ({ ...p, branch: mine[0].id }))
    })
  }, [])
  const save = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/contributions/', { method: 'POST', body: { ...f, quantity: +f.quantity } }); setF({ ...f, name: '', parent_name: '' }); load() } catch (e) { setErr(e.message) }
  }
  return (
    <>
      <h2>Parent contributions <span className="muted">(Primary School)</span></h2>
      {user.role === 'LIBRARIAN' && (branches.length === 0
        ? <p className="muted">Your school is not a Primary school.</p>
        : <form className="card" onSubmit={save}><div className="line">
            <input required placeholder="Item e.g. Soap, Toothpaste" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            <input type="number" min="1" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} />
            <input placeholder="Parent (optional)" value={f.parent_name} onChange={(e) => setF({ ...f, parent_name: e.target.value })} />
            <button className="primary">Record</button></div>{err && <p className="error">{err}</p>}</form>)}
      <section className="card"><table><thead><tr><th>Item</th><th>Qty</th><th>Parent</th><th>Recorded</th></tr></thead>
        <tbody>{rows.map((c) => <tr key={c.id}><td>{c.item_name}</td><td>{c.quantity}</td><td>{c.parent_name || '—'}</td><td>{fmt(c.created_at)}</td></tr>)}</tbody></table></section>
    </>
  )
}

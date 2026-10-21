import { useEffect, useState } from 'react'
import { api, fmt } from '../api'
import { useAuth } from '../auth'

export default function Issuing() {
  const { user } = useAuth()
  const isLib = user.role === 'LIBRARIAN'
  const [loans, setLoans] = useState([])
  const [stock, setStock] = useState([])
  const [students, setStudents] = useState([])
  const [mode, setMode] = useState('book')
  const [f, setF] = useState({ code: '', item: '', quantity: 1, borrower_name: '', borrower_type: 'STUDENT', due_date: '', student: '' })
  const [msg, setMsg] = useState(null)
  const load = () => { api('/issues/?open=1').then(setLoans); api('/items/').then((x) => setStock(x.filter((i) => i.category !== 'BOOK'))) }
  useEffect(() => { load(); if (isLib) api('/students/?status=ACTIVE').then(setStudents) }, [])

  const issue = async (e) => {
    e.preventDefault(); setMsg(null)
    try {
      const who = f.student ? { student: +f.student } : { borrower_name: f.borrower_name, borrower_type: f.borrower_type }
      await api('/issues/', { method: 'POST', body: mode === 'book'
        ? { code: f.code, ...who, due_date: f.due_date }
        : { item: f.item, quantity: +f.quantity, ...who } })
      setMsg({ ok: 'Recorded.' }); setF({ ...f, code: '', borrower_name: '', student: '' }); load()
    } catch (e) { setMsg({ err: e.message }) }
  }
  const ret = async (id) => { await api(`/issues/${id}/return/`, { method: 'POST' }); load() }

  return (
    <>
      <h2>Issuing & returns</h2>
      {isLib && (
        <form className="card" onSubmit={issue}>
          <div className="tabs">
            <button type="button" className={mode === 'book' ? 'on' : ''} onClick={() => setMode('book')}>Book (by code)</button>
            <button type="button" className={mode === 'item' ? 'on' : ''} onClick={() => setMode('item')}>Stationery / uniform (by quantity)</button>
          </div>
          <div className="line">
            {mode === 'book'
              ? <input required placeholder="Book code e.g. GSS-0001-002" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} />
              : <><select required value={f.item} onChange={(e) => setF({ ...f, item: e.target.value })}>
                  <option value="">Choose item…</option>{stock.map((i) => <option key={i.id} value={i.id}>{i.name}{i.size && ` (${i.size})`} — {i.on_hand} in stock</option>)}</select>
                <input type="number" min="1" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></>}
            <select value={f.student} onChange={(e) => setF({ ...f, student: e.target.value })}>
              <option value="">Not a registered student…</option>{students.map((st) => <option key={st.id} value={st.id}>{st.full_name} ({st.admission_no})</option>)}</select>
            {!f.student && <><input required placeholder="Borrower name" value={f.borrower_name} onChange={(e) => setF({ ...f, borrower_name: e.target.value })} />
              <select value={f.borrower_type} onChange={(e) => setF({ ...f, borrower_type: e.target.value })}><option>STUDENT</option><option>TEACHER</option><option>OTHER</option></select></>}
            {mode === 'book' && <input type="date" value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })} />}
            <button className="primary">Issue</button>
          </div>
          {msg?.err && <p className="error">{msg.err}</p>}{msg?.ok && <p className="ok">{msg.ok}</p>}
        </form>
      )}
      <section className="card">
        <h3>Books currently out ({loans.length})</h3>
        <table><thead><tr><th>Code</th><th>Title</th><th>Borrower</th><th>Issued</th><th>Due</th><th></th></tr></thead>
          <tbody>{loans.map((l) => (
            <tr key={l.id}><td className="mono">{l.code}</td><td>{l.item_name}</td><td>{l.borrower_name}</td><td>{fmt(l.issued_at)}</td><td>{l.due_date || '—'}</td>
              <td>{isLib && l.code && <button className="link" onClick={() => ret(l.id)}>Return</button>}</td></tr>))}</tbody></table>
      </section>
    </>
  )
}

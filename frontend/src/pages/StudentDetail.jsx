import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, fmt } from '../api'
import { useAuth } from '../auth'
import { tzs, useLoad } from '../hooks'

export default function StudentDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [s, reloadS] = useLoad(`/students/${id}/`)
  const [loans] = useLoad(user.role === 'PARENT' || ['ADMIN', 'MANAGER', 'LIBRARIAN', 'HEAD_MASTER', 'ACADEMIC_MASTER'].includes(user.role) ? `/students/${id}/loans/` : '')
  const [rep] = useLoad(user.role === 'LIBRARIAN' ? '' : `/reports/student/${id}/`)
  const [inv] = useLoad(['ADMIN', 'MANAGER', 'BURSAR', 'HEAD_MASTER', 'PARENT'].includes(user.role) ? `/invoices/?student=${id}` : '')
  const [ride] = useLoad(`/transport/?student=${id}`)
  const [gs, reloadG] = useLoad(['ADMIN', 'MANAGER', 'BURSAR', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'].includes(user.role) ? `/guardians/?student=${id}` : '')
  const [g, setG] = useState({ full_name: '', phone: '', email: '', relationship: 'Parent' })
  const [err, setErr] = useState('')
  const canManage = ['ADMIN', 'HEAD_MASTER', 'ACADEMIC_MASTER'].includes(user.role)
  const canLogin = ['ADMIN', 'HEAD_MASTER'].includes(user.role)
  if (!s) return <p className="muted">Loading…</p>

  const addGuardian = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/guardians/', { method: 'POST', body: { ...g, students: [+id] } }); setG({ ...g, full_name: '', phone: '', email: '' }); reloadG(); reloadS() } catch (x) { setErr(x.message) }
  }
  const makeLogin = async (gid) => {
    const password = prompt('Choose a password for this parent (8+ characters):'); if (!password) return
    try { await api(`/guardians/${gid}/create_login/`, { method: 'POST', body: { password } }); reloadG() } catch (x) { setErr(x.message) }
  }
  const setStatus = async (status) => { try { await api(`/students/${id}/`, { method: 'PATCH', body: { status } }); reloadS() } catch (x) { setErr(x.message) } }

  return (
    <>
      <div className="bar"><h2>{s.full_name}</h2><span className="pill">{s.status}</span></div>
      <section className="panel-green"><h3>Student details:</h3>
        <div className="fields">
          {[['Admission no.', s.admission_no], ['School', s.branch_name], ['Class', s.class_name || 'No class yet'], ['Gender', s.gender === 'F' ? 'Female' : 'Male'],
            ...(s.date_of_birth ? [['Date of birth', s.date_of_birth]] : [])].map(([k, v]) => <div key={k}><span className="tag">{k}</span><div className="val">{v}</div></div>)}
        </div>
        {canManage && <div className="buttons" style={{ marginTop: 12 }}>{s.status === 'ACTIVE'
          ? <><button onClick={() => setStatus('LEFT')}>Mark as left</button><button onClick={() => setStatus('GRADUATED')}>Mark as graduated</button></>
          : <button onClick={() => setStatus('ACTIVE')}>Reactivate</button>}</div>}
        {err && <p className="error">{err}</p>}
      </section>

      {gs && (
        <section className="card"><h3>Parents / guardians</h3>
          <table><tbody>{gs.map((x) => (
            <tr key={x.id}><td>{x.full_name} <span className="muted">({x.relationship})</span></td><td>{x.phone}</td><td>{x.email}</td>
              <td>{x.has_login ? <span className="pill completed">has login</span> : canLogin && <button className="link" onClick={() => makeLogin(x.id)}>Create login</button>}</td></tr>))}</tbody></table>
          {gs.length === 0 && <p className="muted">No parent recorded yet.</p>}
          {canManage && <form onSubmit={addGuardian} className="line">
            <input required placeholder="Parent name" value={g.full_name} onChange={(e) => setG({ ...g, full_name: e.target.value })} />
            <input placeholder="Phone" value={g.phone} onChange={(e) => setG({ ...g, phone: e.target.value })} />
            <input type="email" placeholder="Email (for login)" value={g.email} onChange={(e) => setG({ ...g, email: e.target.value })} />
            <input placeholder="Relationship" value={g.relationship} onChange={(e) => setG({ ...g, relationship: e.target.value })} />
            <button className="primary">Add parent</button></form>}
        </section>)}

      {rep && (
        <section className="card"><h3>Academic report</h3>
          {rep.attendance.days > 0 && <p>Attendance: <b>{rep.attendance.percent}%</b> <span className="muted">({rep.attendance.present} present, {rep.attendance.late} late, {rep.attendance.absent} absent of {rep.attendance.days} days)</span></p>}
          {rep.terms.length === 0 && <p className="muted">No marks entered yet.</p>}
          {rep.terms.map((t) => (
            <div key={t.term}><h4>{t.term} {t.overall != null && <span className="pill">overall {t.overall}%</span>}</h4>
              <table><thead><tr><th>Subject</th><th>Results</th><th>Average</th></tr></thead>
                <tbody>{t.subjects.map((x) => <tr key={x.subject}><td>{x.subject}</td><td>{x.results.map((r) => `${r.assessment}: ${+r.score}/${r.max}`).join(' · ')}</td><td><b>{x.average}%</b></td></tr>)}</tbody></table></div>))}
        </section>)}

      {inv && (
        <section className="card"><h3>Fees</h3>
          <table><thead><tr><th>Fee</th><th>Amount</th><th>Paid</th><th>Balance</th><th>Receipts</th></tr></thead>
            <tbody>{inv.map((i) => <tr key={i.id}><td>{i.fee_name}</td><td>{tzs(i.amount)}</td><td>{tzs(i.paid)}</td>
              <td className={+i.balance > 0 ? 'error' : 'ok'}>{tzs(i.balance)}</td><td className="mono">{i.payments.map((p) => p.receipt_no).join(', ')}</td></tr>)}</tbody></table>
          {inv.length === 0 && <p className="muted">No fees billed yet.</p>}
        </section>)}

      {ride && ride.length > 0 && <section className="card"><h3>School transport</h3><p>{ride[0].route_name}{ride[0].pickup_point && ` · pick-up: ${ride[0].pickup_point}`}</p></section>}

      {loans && (
        <section className="card"><h3>Library</h3>
          <table><thead><tr><th>Code</th><th>Item</th><th>Issued</th><th>Due</th><th>Returned</th></tr></thead>
            <tbody>{loans.map((l) => <tr key={l.id}><td className="mono">{l.code || '—'}</td><td>{l.item_name}{l.quantity > 1 && ` ×${l.quantity}`}</td><td>{fmt(l.issued_at)}</td><td>{l.due_date || '—'}</td><td>{l.copy ? (l.returned_at ? fmt(l.returned_at) : <b>Still out</b>) : 'Issued'}</td></tr>)}</tbody></table>
          {loans.length === 0 && <p className="muted">Nothing borrowed yet.</p>}
        </section>)}
    </>
  )
}

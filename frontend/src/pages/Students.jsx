import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { BranchPicker, MANAGERS, useBranches, useLoad } from '../hooks'

export default function Students() {
  const { user } = useAuth()
  const b = useBranches()
  const [q, setQ] = useState('')
  const [room, setRoom] = useState('')
  const [rows, reload] = useLoad(b.branch ? `/students/?branch=${b.branch}&q=${encodeURIComponent(q)}${room ? '&classroom=' + room : ''}` : '', [])
  const [rooms] = useLoad(b.branch ? `/classes/?branch=${b.branch}` : '', [])
  const [f, setF] = useState({ admission_no: '', full_name: '', gender: 'F', date_of_birth: '', classroom: '' })
  const [err, setErr] = useState('')
  const add = async (e) => {
    e.preventDefault(); setErr('')
    try {
      await api('/students/', { method: 'POST', body: { ...f, branch: b.branch, classroom: f.classroom || null, date_of_birth: f.date_of_birth || null } })
      setF({ ...f, admission_no: '', full_name: '' }); reload()
    } catch (x) { setErr(x.message) }
  }
  return (
    <>
      <div className="bar"><h2>Students</h2><BranchPicker {...b} /></div>
      {MANAGERS.includes(user.role) && (
        <form className="card" onSubmit={add}><h3>Register a student</h3>
          <div className="line">
            <input required placeholder="Admission no." value={f.admission_no} onChange={(e) => setF({ ...f, admission_no: e.target.value })} />
            <input required placeholder="Full name" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
            <select value={f.gender} onChange={(e) => setF({ ...f, gender: e.target.value })}><option value="F">Female</option><option value="M">Male</option></select>
            <input type="date" title="Date of birth" value={f.date_of_birth} onChange={(e) => setF({ ...f, date_of_birth: e.target.value })} />
            <select value={f.classroom} onChange={(e) => setF({ ...f, classroom: e.target.value })}><option value="">No class yet</option>{(rooms || []).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
            <button className="primary">Register</button></div>
          {err && <p className="error">{err}</p>}
        </form>)}
      <section className="card">
        <div className="line"><input placeholder="Search name or admission no." value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={room} onChange={(e) => setRoom(e.target.value)}><option value="">All classes</option>{(rooms || []).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></div>
        <table><thead><tr><th>Adm. no.</th><th>Name</th><th>Class</th><th>Parents</th><th>Status</th></tr></thead>
          <tbody>{(rows || []).map((s) => (
            <tr key={s.id}><td className="mono">{s.admission_no}</td><td><Link to={`/students/${s.id}`}>{s.full_name}</Link></td><td>{s.class_name || '—'}</td>
              <td>{s.guardian_names.join(', ') || '—'}</td><td><span className={'pill ' + (s.status === 'ACTIVE' ? 'completed' : '')}>{s.status}</span></td></tr>))}</tbody></table>
        {rows && rows.length === 0 && <p className="muted">No students found.</p>}
      </section>
    </>
  )
}

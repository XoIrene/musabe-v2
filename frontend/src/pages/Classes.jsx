import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { BranchPicker, MANAGERS, useBranches, useLoad } from '../hooks'

export default function Classes() {
  const { user } = useAuth()
  const b = useBranches()
  const [rows, reload] = useLoad(b.branch ? `/classes/?branch=${b.branch}` : '', [])
  const [staff, setStaff] = useState([])
  const [name, setName] = useState('')
  const [err, setErr] = useState('')
  const canEdit = MANAGERS.includes(user.role)
  useEffect(() => { if (user.role === 'ADMIN') api('/staff/').then(setStaff) }, [])
  const add = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/classes/', { method: 'POST', body: { branch: b.branch, name } }); setName(''); reload() } catch (x) { setErr(x.message) }
  }
  const setTeacher = async (id, t) => {
    try { await api(`/classes/${id}/`, { method: 'PATCH', body: { class_teacher: t || null } }); reload() } catch (x) { setErr(x.message) }
  }
  const teachers = staff.filter((s) => s.role === 'STAFF' && s.branches.includes(b.branch))
  return (
    <>
      <div className="bar"><h2>Classes</h2><BranchPicker {...b} /></div>
      {canEdit && <form className="card" onSubmit={add}><div className="line"><input required placeholder="New class e.g. Form 3 Green" value={name} onChange={(e) => setName(e.target.value)} /><button className="primary">Add class</button></div></form>}
      {err && <p className="error">{err}</p>}
      <section className="card"><table><thead><tr><th>Class</th><th>Students</th><th>Class teacher</th></tr></thead>
        <tbody>{(rows || []).map((r) => (
          <tr key={r.id}><td>{r.name}</td><td>{r.student_count}</td>
            <td>{user.role === 'ADMIN'
              ? <select value={r.class_teacher || ''} onChange={(e) => setTeacher(r.id, e.target.value)}><option value="">—</option>{teachers.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}</select>
              : r.class_teacher_name || '—'}</td></tr>))}</tbody></table></section>
    </>
  )
}

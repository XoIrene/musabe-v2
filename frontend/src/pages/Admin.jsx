import { useEffect, useState } from 'react'
import { api } from '../api'

const ROLES = [['MANAGER', 'Manager'], ['BURSAR', 'Bursar'], ['STOREKEEPER', 'Storekeeper'], ['ADMIN', 'Admin'],
  ['HEAD_MASTER', 'Head Master / Headmistress'], ['ACADEMIC_MASTER', 'Academic Master'], ['LIBRARIAN', 'Librarian'], ['STAFF', 'Requesting Staff']]
const CENTRAL = ['ADMIN', 'MANAGER', 'BURSAR', 'STOREKEEPER']

export default function Admin() {
  const [branches, setBranches] = useState([])
  const [staff, setStaff] = useState([])
  const [b, setB] = useState({ name: '', code: '', type: 'SECONDARY' })
  const [u, setU] = useState({ full_name: '', email: '', password: '', role: 'STAFF', branches: [] })
  const [err, setErr] = useState('')
  const load = () => { api('/branches/').then(setBranches); api('/staff/').then(setStaff) }
  useEffect(load, [])

  const addBranch = async (e) => { e.preventDefault(); setErr(''); try { await api('/branches/', { method: 'POST', body: b }); setB({ name: '', code: '', type: 'SECONDARY' }); load() } catch (e) { setErr(e.message) } }
  const addStaff = async (e) => {
    e.preventDefault(); setErr('')
    try { await api('/staff/', { method: 'POST', body: { ...u, branches: CENTRAL.includes(u.role) ? [] : u.branches } }); setU({ ...u, full_name: '', email: '', password: '' }); load() }
    catch (e) { setErr(e.message) }
  }
  const toggle = (id) => setU({ ...u, branches: u.branches.includes(id) ? u.branches.filter((x) => x !== id) : [...u.branches, id] })

  return (
    <>
      <h2>Branches & Staff</h2>
      {err && <p className="error">{err}</p>}
      <form className="card" onSubmit={addBranch}>
        <h3>1. Register a school branch</h3>
        <div className="line">
          <input required placeholder="Name" value={b.name} onChange={(e) => setB({ ...b, name: e.target.value })} />
          <input required placeholder="Code (e.g. GSS)" maxLength="10" value={b.code} onChange={(e) => setB({ ...b, code: e.target.value.toUpperCase() })} />
          <select value={b.type} onChange={(e) => setB({ ...b, type: e.target.value })}><option value="PRIMARY">Primary</option><option value="SECONDARY">Secondary</option></select>
          <button className="primary">Add branch</button>
        </div>
        <p className="muted">{branches.map((x) => `${x.name} (${x.type.toLowerCase()})`).join(' · ')}</p>
      </form>
      <form className="card" onSubmit={addStaff}>
        <h3>2. Register a staff member</h3>
        <div className="line">
          <input required placeholder="Full name" value={u.full_name} onChange={(e) => setU({ ...u, full_name: e.target.value })} />
          <input required type="email" placeholder="Email" value={u.email} onChange={(e) => setU({ ...u, email: e.target.value })} />
          <input required type="password" minLength="8" placeholder="Password (8+)" value={u.password} onChange={(e) => setU({ ...u, password: e.target.value })} />
          <select value={u.role} onChange={(e) => setU({ ...u, role: e.target.value })}>{ROLES.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        </div>
        {CENTRAL.includes(u.role)
          ? <p className="muted">Place: Central Administration</p>
          : <p>Place: {branches.map((x) => <label key={x.id} className="check"><input type="checkbox" checked={u.branches.includes(x.id)} onChange={() => toggle(x.id)} /> {x.name}</label>)}</p>}
        <button className="primary">Register staff</button>
      </form>
      <section className="card"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Place</th></tr></thead>
        <tbody>{staff.map((s) => <tr key={s.id}><td>{s.full_name}</td><td>{s.email}</td><td>{s.role_label}</td><td>{s.branch_names.join(', ') || 'Central Administration'}</td></tr>)}</tbody></table></section>
    </>
  )
}

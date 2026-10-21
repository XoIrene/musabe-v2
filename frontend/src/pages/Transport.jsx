import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { BranchPicker, useBranches, useLoad } from '../hooks'

export default function Transport() {
  const { user } = useAuth()
  const canEdit = ['ADMIN', 'HEAD_MASTER'].includes(user.role)
  const b = useBranches()
  const [routes, reloadR] = useLoad(b.branch ? `/routes/?_=${b.branch}` : '', [b.branch])
  const [riders, reloadA] = useLoad('/transport/')
  const [students] = useLoad(canEdit && b.branch ? `/students/?branch=${b.branch}&status=ACTIVE` : '', [b.branch])
  const [r, setR] = useState({ name: '', vehicle: '', driver_name: '', driver_phone: '', capacity: 30, stops: '' })
  const [a, setA] = useState({ student: '', route: '', pickup_point: '' })
  const [err, setErr] = useState('')
  const run = async (fn) => { setErr(''); try { await fn() } catch (x) { setErr(x.message) } }
  const mine = (routes || []).filter((x) => x.branch === b.branch)
  const assigned = new Set((riders || []).map((x) => x.student))
  return (
    <>
      <div className="bar"><h2>School transport</h2><BranchPicker {...b} /></div>
      {err && <p className="error">{err}</p>}
      {canEdit && <form className="card" onSubmit={(e) => { e.preventDefault(); run(async () => { await api('/routes/', { method: 'POST', body: { ...r, branch: b.branch, capacity: +r.capacity } }); setR({ ...r, name: '', stops: '' }); reloadR() }) }}>
        <h3>New route</h3><div className="line">
          <input required placeholder="Route name" value={r.name} onChange={(e) => setR({ ...r, name: e.target.value })} />
          <input placeholder="Vehicle plate" value={r.vehicle} onChange={(e) => setR({ ...r, vehicle: e.target.value })} />
          <input placeholder="Driver" value={r.driver_name} onChange={(e) => setR({ ...r, driver_name: e.target.value })} />
          <input placeholder="Driver phone" value={r.driver_phone} onChange={(e) => setR({ ...r, driver_phone: e.target.value })} />
          <input type="number" min="1" title="Seats" value={r.capacity} onChange={(e) => setR({ ...r, capacity: e.target.value })} /></div>
        <textarea rows="2" placeholder="Stops, one per line" value={r.stops} onChange={(e) => setR({ ...r, stops: e.target.value })} />
        <button className="primary">Add route</button></form>}
      <section className="card"><h3>Routes</h3>
        <table><thead><tr><th>Route</th><th>Vehicle / driver</th><th>Seats</th><th>Stops</th></tr></thead>
          <tbody>{mine.map((x) => <tr key={x.id}><td>{x.name}</td><td>{x.vehicle} · {x.driver_name} {x.driver_phone}</td><td>{x.riders}/{x.capacity}</td><td style={{ whiteSpace: 'pre-line' }}>{x.stops}</td></tr>)}</tbody></table></section>
      {canEdit && <form className="card" onSubmit={(e) => { e.preventDefault(); run(async () => { await api('/transport/', { method: 'POST', body: a }); setA({ ...a, student: '' }); reloadA(); reloadR() }) }}>
        <h3>Put a student on a route</h3><div className="line">
          <select required value={a.student} onChange={(e) => setA({ ...a, student: e.target.value })}><option value="">Student…</option>{(students || []).filter((s) => !assigned.has(s.id)).map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.admission_no})</option>)}</select>
          <select required value={a.route} onChange={(e) => setA({ ...a, route: e.target.value })}><option value="">Route…</option>{mine.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
          <input placeholder="Pick-up point" value={a.pickup_point} onChange={(e) => setA({ ...a, pickup_point: e.target.value })} />
          <button className="primary">Assign</button></div></form>}
      <section className="card"><h3>Riders</h3>
        <table><tbody>{(riders || []).filter((x) => mine.some((m) => m.id === x.route)).map((x) => <tr key={x.id}><td>{x.student_name}</td><td className="muted">{x.admission_no}</td><td>{x.route_name}</td><td>{x.pickup_point}</td>
          <td>{canEdit && <button className="link" onClick={() => run(async () => { await api(`/transport/${x.id}/`, { method: 'DELETE' }); reloadA(); reloadR() })}>Remove</button>}</td></tr>)}</tbody></table></section>
    </>
  )
}

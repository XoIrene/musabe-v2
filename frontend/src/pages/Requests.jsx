import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt, STATUS } from '../api'
import { useAuth } from '../auth'

export default function Requests() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [kind, setKind] = useState('')
  useEffect(() => { api('/requests/' + (kind ? `?kind=${kind}` : '')).then(setRows) }, [kind])
  const school = user.branches.length > 0
  return (
    <>
      <div className="bar">
        <h2>Requests</h2>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">All kinds</option><option value="BOOKS">Books</option><option value="OTHER">Other items</option>
        </select>
        {school && <Link className="primary btn" to="/requests/new">+ New request</Link>}
      </div>
      <section className="card">
        <table>
          <thead><tr><th>#</th><th>Title</th><th>Kind</th><th>School</th><th>Requestor</th><th>Status</th><th>Raised</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/requests/${r.id}`}>{r.id}</Link></td><td><Link to={`/requests/${r.id}`}>{r.title}</Link></td>
              <td>{r.kind === 'BOOKS' ? 'Books' : 'Other'}</td><td>{r.branch_name}</td><td>{r.requestor_name}</td>
              <td><span className={'pill ' + r.status.toLowerCase()}>{STATUS[r.status]}</span></td><td>{fmt(r.created_at)}</td>
            </tr>
          ))}</tbody>
        </table>
        {rows.length === 0 && <p className="muted">No requests yet.</p>}
      </section>
    </>
  )
}

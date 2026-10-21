import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, STATUS } from '../api'
import { useAuth } from '../auth'

export default function Dashboard() {
  const { user } = useAuth()
  const [todo, setTodo] = useState([])
  const [rep, setRep] = useState(null)
  useEffect(() => {
    api('/requests/?todo=1').then(setTodo)
    api('/reports/summary/').then(setRep)
  }, [])
  return (
    <>
      <h2>Hello, {user.full_name.split(' ')[0]}</h2>
      <section className="card">
        <h3>Waiting for you ({todo.length})</h3>
        {todo.length === 0 && <p className="muted">Nothing needs your action right now.</p>}
        {todo.map((r) => (
          <Link key={r.id} to={`/requests/${r.id}`} className="row">
            <span><b>#{r.id}</b> {r.title}</span><span className="muted">{r.branch_name}</span>
            <span className="pill">{STATUS[r.status]}</span>
          </Link>
        ))}
      </section>
      {rep && (
        <>
          <section className="grid">
            <div className="stat"><b>{rep.open_loans}</b><span>items on loan</span></div>
            {Object.entries(rep.pending_requests_by_waiting_on).map(([k, n]) => (
              <div className="stat" key={k}><b>{n}</b><span>waiting on {k}</span></div>
            ))}
          </section>
          <section className="card">
            <h3>Live stock</h3>
            <table>
              <thead><tr><th>School</th><th>Book titles</th><th>Available</th><th>Issued</th><th>Lost / damaged</th><th>Written off</th><th>Other items</th><th>Low stock</th></tr></thead>
              <tbody>{rep.branches.map((b) => (
                <tr key={b.branch}><td>{b.branch}</td><td>{b.book_titles}</td><td>{b.copies_available}</td><td>{b.copies_issued}</td>
                  <td>{b.copies_lost_or_damaged}</td><td>{b.copies_written_off}</td><td>{b.other_items_in_stock}</td>
                  <td>{b.low_stock.join(', ') || '—'}</td></tr>
              ))}</tbody>
            </table>
          </section>
        </>
      )}
    </>
  )
}

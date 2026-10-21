import { Fragment, useEffect, useState } from 'react'
import { api, CATEGORIES } from '../api'

export default function Inventory() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('')
  const [open, setOpen] = useState(null)
  const [copies, setCopies] = useState([])
  useEffect(() => { api(`/items/?q=${encodeURIComponent(q)}&category=${cat}`).then(setItems) }, [q, cat])
  const show = (it) => {
    if (open === it.id) return setOpen(null)
    setOpen(it.id); api(`/copies/?item=${it.id}`).then(setCopies)
  }
  return (
    <>
      <div className="bar">
        <h2>Library & Store</h2>
        <input placeholder="Search title or author" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={cat} onChange={(e) => setCat(e.target.value)}>
          <option value="">All categories</option>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <section className="card">
        <table>
          <thead><tr><th>Item</th><th>Category</th><th>School</th><th>In stock</th><th></th></tr></thead>
          <tbody>{items.map((it) => (
            <Fragment key={it.id}>
              <tr>
                <td>{it.name}{it.author && <span className="muted"> — {it.author}</span>}{it.size && ` (${it.size})`}</td>
                <td>{CATEGORIES[it.category]}</td><td>{it.branch_name}</td>
                <td>{it.on_hand}{it.total_copies != null && <span className="muted"> of {it.total_copies}</span>}{it.low && it.category !== 'BOOK' && <span className="pill rejected">low</span>}</td>
                <td>{it.category === 'BOOK' && <button className="link" onClick={() => show(it)}>{open === it.id ? 'hide copies' : 'copies'}</button>}</td>
              </tr>
              {open === it.id && <tr><td colSpan="5">
                {copies.map((c) => <span key={c.id} className={'code ' + c.status.toLowerCase()} title={c.borrower || c.status}>{c.code}</span>)}
              </td></tr>}
            </Fragment>
          ))}</tbody>
        </table>
        {items.length === 0 && <p className="muted">Nothing in stock yet. Stock appears when the Librarian receives a delivery.</p>}
      </section>
    </>
  )
}

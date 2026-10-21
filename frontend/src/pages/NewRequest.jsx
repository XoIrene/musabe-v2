import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, CATEGORIES } from '../api'
import { useAuth } from '../auth'

export default function NewRequest() {
  const { user } = useAuth()
  const nav = useNavigate()
  const [kind, setKind] = useState('BOOKS')
  const [branch, setBranch] = useState(user.branches[0])
  const [branches, setBranches] = useState([])
  const [title, setTitle] = useState('')
  const [why, setWhy] = useState('')
  const blank = { name: '', author: '', category: 'STATIONERY', quantity: 1, size: '' }
  const [lines, setLines] = useState([{ ...blank }])
  const [err, setErr] = useState('')
  useEffect(() => { api('/branches/').then(setBranches) }, [])

  const set = (i, k, v) => setLines(lines.map((l, j) => (j === i ? { ...l, [k]: v } : l)))
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    try {
      const r = await api('/requests/', { method: 'POST', body: { kind, branch, title, justification: why,
        lines: lines.map((l) => ({ ...l, quantity: +l.quantity, category: kind === 'BOOKS' ? 'BOOK' : l.category })) } })
      nav(`/requests/${r.id}`)
    } catch (e) { setErr(e.message) }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h2>New request</h2>
      <div className="two">
        <label>What are you buying?
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="BOOKS">Books / textbooks (full approval chain)</option>
            <option value="OTHER">Stationery, uniforms, vitambaa, Primary items (shorter chain)</option>
          </select></label>
        <label>School
          <select value={branch} onChange={(e) => setBranch(+e.target.value)}>
            {branches.filter((b) => user.branches.includes(b.id)).map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select></label>
      </div>
      <label>Title<input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Form 1 Biology textbooks" /></label>
      <label>Why is it needed?<textarea value={why} onChange={(e) => setWhy(e.target.value)} /></label>
      <h3>Items</h3>
      {lines.map((l, i) => (
        <div className="line" key={i}>
          <input required placeholder={kind === 'BOOKS' ? 'Book title' : 'Item'} value={l.name} onChange={(e) => set(i, 'name', e.target.value)} />
          {kind === 'BOOKS'
            ? <input placeholder="Author" value={l.author} onChange={(e) => set(i, 'author', e.target.value)} />
            : <><select value={l.category} onChange={(e) => set(i, 'category', e.target.value)}>
                {Object.entries(CATEGORIES).filter(([k]) => k !== 'BOOK').map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
              <input placeholder="Size (optional)" value={l.size} onChange={(e) => set(i, 'size', e.target.value)} /></>}
          <input type="number" min="1" value={l.quantity} onChange={(e) => set(i, 'quantity', e.target.value)} />
          {lines.length > 1 && <button type="button" className="link" onClick={() => setLines(lines.filter((_, j) => j !== i))}>remove</button>}
        </div>
      ))}
      <button type="button" className="link" onClick={() => setLines([...lines, { ...blank }])}>+ add item</button>
      {err && <p className="error">{err}</p>}
      <p><button className="primary">Send request</button></p>
    </form>
  )
}

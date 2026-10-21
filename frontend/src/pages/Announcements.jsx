import { useState } from 'react'
import { api, fmt } from '../api'
import { useAuth } from '../auth'
import { useLoad } from '../hooks'

export default function Announcements() {
  const { user } = useAuth()
  const canPost = ['ADMIN', 'MANAGER', 'HEAD_MASTER'].includes(user.role)
  const central = user.role !== 'HEAD_MASTER'
  const [rows, reload] = useLoad('/announcements/')
  const [branches] = useLoad(canPost ? '/branches/' : '')
  const [f, setF] = useState({ title: '', body: '', audience: 'ALL', branch: '' })
  const [err, setErr] = useState('')
  const mineBranches = (branches || []).filter((b) => central || user.branches.includes(b.id))
  const post = async (e) => {
    e.preventDefault(); setErr('')
    try {
      await api('/announcements/', { method: 'POST', body: { ...f, branch: f.branch || (central ? null : mineBranches[0]?.id) } })
      setF({ ...f, title: '', body: '' }); reload()
    } catch (x) { setErr(x.message) }
  }
  const remove = async (id) => { if (confirm('Remove this notice?')) { await api(`/announcements/${id}/`, { method: 'DELETE' }); reload() } }
  return (
    <>
      <h2>Announcements</h2>
      {canPost && (
        <form className="card" onSubmit={post}>
          <input required placeholder="Title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
          <textarea required rows="3" placeholder="Message" value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} style={{ margin: '8px 0' }} />
          <div className="line">
            <select value={f.branch} onChange={(e) => setF({ ...f, branch: e.target.value })}>{central && <option value="">All schools</option>}{mineBranches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
            <select value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}><option value="ALL">Everyone</option><option value="STAFF">Staff only</option><option value="PARENTS">Parents only</option></select>
            <button className="primary">Post</button></div>
          {err && <p className="error">{err}</p>}
        </form>)}
      {(rows || []).map((a) => (
        <section className="card" key={a.id}>
          <h3>{a.title} <span className="pill">{a.branch_name}</span>{a.audience !== 'ALL' && <span className="pill">{a.audience === 'STAFF' ? 'staff' : 'parents'}</span>}</h3>
          <p style={{ whiteSpace: 'pre-line' }}>{a.body}</p>
          <small className="muted">{a.author_name} · {fmt(a.created_at)}</small>
          {canPost && (['ADMIN', 'MANAGER'].includes(user.role) || a.author_name === user.full_name) && <button className="link" onClick={() => remove(a.id)}>Remove</button>}
        </section>))}
      {rows && rows.length === 0 && <p className="muted">No announcements.</p>}
    </>
  )
}

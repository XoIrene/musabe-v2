import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../api'
import { useAuth } from '../auth'
import { tzs } from '../hooks'

export default function ParentHome() {
  const { user } = useAuth()
  const [kids, setKids] = useState([])
  const [info, setInfo] = useState({})
  const [news, setNews] = useState([])
  useEffect(() => {
    api('/announcements/').then((n) => setNews(n.slice(0, 3)))
    api('/students/').then(async (list) => {
      setKids(list)
      const out = {}
      for (const s of list) {
        const [inv, rep, loans] = await Promise.all([api(`/invoices/?student=${s.id}`), api(`/reports/student/${s.id}/`), api(`/students/${s.id}/loans/`)])
        out[s.id] = { owed: inv.reduce((n, i) => n + +i.balance, 0), att: rep.attendance.percent, out: loans.filter((l) => l.copy && !l.returned_at).length }
      }
      setInfo(out)
    })
  }, [])
  return (
    <>
      <h2>Hello, {user.full_name}</h2>
      <section className="grid">{kids.map((s) => {
        const i = info[s.id]
        return (
          <Link to={`/students/${s.id}`} key={s.id} className="stat" style={{ textDecoration: 'none', color: 'inherit' }}>
            <b style={{ fontSize: 18 }}>{s.full_name}</b><span>{s.class_name || 'No class'} · {s.branch_name}</span>
            {i && <p style={{ margin: '8px 0 0' }}>Fees owed: <b className={i.owed > 0 ? 'error' : 'ok'}>{tzs(i.owed)}</b><br />Attendance: <b>{i.att != null ? i.att + '%' : '—'}</b><br />Books out: <b>{i.out}</b></p>}
          </Link>)
      })}</section>
      {kids.length === 0 && <p className="muted">No children are linked to your account yet. Please contact the school.</p>}
      <section className="card"><h3>Latest announcements</h3>
        {news.map((a) => <p key={a.id}><b>{a.title}</b> <span className="muted">· {fmt(a.created_at)}</span><br />{a.body}</p>)}
        {news.length === 0 && <p className="muted">Nothing new.</p>}
      </section>
    </>
  )
}

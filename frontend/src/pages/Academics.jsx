import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { BranchPicker, MANAGERS, useBranches, useLoad } from '../hooks'

const today = () => new Date().toISOString().slice(0, 10)

export default function Academics() {
  const [tab, setTab] = useState('marks')
  const b = useBranches()
  return (
    <>
      <div className="bar"><h2>Academics</h2><BranchPicker {...b} /></div>
      <div className="tabs">{[['marks', 'Tests & marks'], ['attendance', 'Attendance'], ['setup', 'Terms & subjects']].map(([k, l]) =>
        <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>
      {b.branch && (tab === 'marks' ? <Marks branch={b.branch} /> : tab === 'attendance' ? <Register branch={b.branch} /> : <Setup branch={b.branch} />)}
    </>
  )
}

function Marks({ branch }) {
  const { user } = useAuth()
  const canEnter = !['ADMIN', 'MANAGER'].includes(user.role)
  const [terms] = useLoad(`/terms/?branch=${branch}`, [branch])
  const [subjects] = useLoad(`/subjects/?branch=${branch}`, [branch])
  const [rooms] = useLoad(`/classes/?branch=${branch}`, [branch])
  const [list, reload] = useLoad(`/assessments/?_=${branch}`, [branch])
  const [f, setF] = useState({ term: '', subject: '', classroom: '', name: '', max_score: 100 })
  const [open, setOpen] = useState(null)
  const [rows, setRows] = useState([])
  const [msg, setMsg] = useState(null)
  const mine = (list || []).filter((a) => a.branch === branch)

  const create = async (e) => {
    e.preventDefault(); setMsg(null)
    try { await api('/assessments/', { method: 'POST', body: { ...f, max_score: +f.max_score } }); reload(); setF({ ...f, name: '' }) } catch (x) { setMsg({ err: x.message }) }
  }
  const load = async (a) => { setOpen(a); setMsg(null); setRows((await api(`/assessments/${a.id}/marks/`)).students) }
  const save = async () => {
    try {
      await api(`/assessments/${open.id}/marks/`, { method: 'POST', body: { marks: rows.map((r) => ({ student: r.student, score: r.score })) } })
      setMsg({ ok: 'Marks saved.' }); reload()
    } catch (x) { setMsg({ err: x.message }) }
  }
  return (
    <>
      {canEnter && (
        <form className="card" onSubmit={create}><h3>New test / exam</h3>
          <div className="line">
            <select required value={f.term} onChange={(e) => setF({ ...f, term: e.target.value })}><option value="">Term…</option>{(terms || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
            <select required value={f.classroom} onChange={(e) => setF({ ...f, classroom: e.target.value })}><option value="">Class…</option>{(rooms || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
            <select required value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })}><option value="">Subject…</option>{(subjects || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
            <input required placeholder="Name e.g. Midterm" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            <input type="number" min="1" title="Maximum score" value={f.max_score} onChange={(e) => setF({ ...f, max_score: e.target.value })} />
            <button className="primary">Create</button></div>
        </form>)}
      <section className="card"><h3>Tests & exams</h3>
        <table><thead><tr><th>Test</th><th>Subject</th><th>Class</th><th>Term</th><th>Marked</th><th></th></tr></thead>
          <tbody>{mine.map((a) => <tr key={a.id}><td>{a.name} <span className="muted">/{a.max_score}</span></td><td>{a.subject_name}</td><td>{a.class_name}</td><td>{a.term_name}</td><td>{a.marked}</td>
            <td><button className="link" onClick={() => load(a)}>{canEnter ? 'Enter marks' : 'View'}</button></td></tr>)}</tbody></table>
        {mine.length === 0 && <p className="muted">No tests yet.</p>}
      </section>
      {open && (
        <section className="card"><h3>{open.name} — {open.subject_name}, {open.class_name} <span className="muted">(out of {open.max_score})</span></h3>
          <table><tbody>{rows.map((r, i) => (
            <tr key={r.student}><td className="mono">{r.admission_no}</td><td>{r.full_name}</td>
              <td style={{ width: 110 }}><input type="number" min="0" max={open.max_score} step="0.5" disabled={!canEnter} value={r.score ?? ''}
                onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, score: e.target.value } : x)))} /></td></tr>))}</tbody></table>
          {canEnter && <button className="primary" onClick={save}>Save marks</button>}
          {msg?.err && <p className="error">{msg.err}</p>}{msg?.ok && <p className="ok">{msg.ok}</p>}
        </section>)}
    </>
  )
}

function Register({ branch }) {
  const { user } = useAuth()
  const canTake = !['ADMIN', 'MANAGER'].includes(user.role)
  const [rooms] = useLoad(`/classes/?branch=${branch}`, [branch])
  const [room, setRoom] = useState('')
  const [date, setDate] = useState(today())
  const [rows, setRows] = useState([])
  const [msg, setMsg] = useState(null)
  useEffect(() => {
    if (!room) return setRows([])
    api(`/attendance/?classroom=${room}&date=${date}`).then((d) => setRows(d.students)).catch((x) => setMsg({ err: x.message }))
  }, [room, date])
  const save = async () => {
    try {
      await api('/attendance/mark/', { method: 'POST', body: { classroom: +room, date, records: rows.filter((r) => r.status).map((r) => ({ student: r.student, status: r.status })) } })
      setMsg({ ok: 'Register saved.' })
    } catch (x) { setMsg({ err: x.message }) }
  }
  const set = (i, status) => setRows(rows.map((x, j) => (j === i ? { ...x, status } : x)))
  return (
    <section className="card"><h3>Class register</h3>
      <div className="line"><select value={room} onChange={(e) => setRoom(e.target.value)}><option value="">Choose class…</option>{(rooms || []).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
        <input type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} /></div>
      <table><tbody>{rows.map((r, i) => (
        <tr key={r.student}><td className="mono">{r.admission_no}</td><td>{r.full_name}</td>
          <td>{[['P', 'Present'], ['L', 'Late'], ['A', 'Absent']].map(([k, l]) => (
            <label className="check" key={k}><input type="radio" disabled={!canTake} checked={r.status === k} onChange={() => set(i, k)} />{l}</label>))}</td></tr>))}</tbody></table>
      {rows.length > 0 && canTake && <div className="buttons"><button onClick={() => setRows(rows.map((r) => ({ ...r, status: r.status || 'P' })))}>Everyone else present</button><button className="primary" onClick={save}>Save register</button></div>}
      {msg?.err && <p className="error">{msg.err}</p>}{msg?.ok && <p className="ok">{msg.ok}</p>}
    </section>
  )
}

function Setup({ branch }) {
  const { user } = useAuth()
  const canEdit = MANAGERS.includes(user.role)
  const [terms, reloadT] = useLoad(`/terms/?branch=${branch}`, [branch])
  const [subjects, reloadS] = useLoad(`/subjects/?branch=${branch}`, [branch])
  const [t, setT] = useState({ name: '', start_date: '', end_date: '' })
  const [sub, setSub] = useState('')
  const [err, setErr] = useState('')
  const run = async (fn) => { setErr(''); try { await fn() } catch (x) { setErr(x.message) } }
  return (
    <div className="two">
      <section className="card"><h3>Terms</h3>
        <table><tbody>{(terms || []).map((x) => <tr key={x.id}><td>{x.name}</td><td className="muted">{x.start_date} → {x.end_date}</td></tr>)}</tbody></table>
        {canEdit && <form className="line" onSubmit={(e) => { e.preventDefault(); run(async () => { await api('/terms/', { method: 'POST', body: { ...t, branch } }); setT({ name: '', start_date: '', end_date: '' }); reloadT() }) }}>
          <input required placeholder="Term 1 2027" value={t.name} onChange={(e) => setT({ ...t, name: e.target.value })} />
          <input required type="date" value={t.start_date} onChange={(e) => setT({ ...t, start_date: e.target.value })} />
          <input required type="date" value={t.end_date} onChange={(e) => setT({ ...t, end_date: e.target.value })} />
          <button className="primary">Add</button></form>}
      </section>
      <section className="card"><h3>Subjects</h3>
        <p>{(subjects || []).map((x) => <span className="pill" key={x.id}>{x.name}</span>)}</p>
        {canEdit && <form className="line" onSubmit={(e) => { e.preventDefault(); run(async () => { await api('/subjects/', { method: 'POST', body: { branch, name: sub } }); setSub(''); reloadS() }) }}>
          <input required placeholder="New subject" value={sub} onChange={(e) => setSub(e.target.value)} /><button className="primary">Add</button></form>}
        {err && <p className="error">{err}</p>}
      </section>
    </div>
  )
}

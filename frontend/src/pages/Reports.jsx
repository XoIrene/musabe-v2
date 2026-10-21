import { useEffect, useState } from 'react'
import { api, download } from '../api'
import { useAuth } from '../auth'
import { tzs } from '../hooks'

const ALL = [
  ['overdue', 'Overdue loans', ['ADMIN', 'MANAGER', 'STOREKEEPER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'], false],
  ['requests', 'Purchase requests', ['ADMIN', 'MANAGER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'], true],
  ['stock', 'Stock levels', ['ADMIN', 'MANAGER', 'STOREKEEPER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'], false],
  ['movements', 'Stock movements', ['ADMIN', 'MANAGER', 'STOREKEEPER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'], true],
  ['fees', 'Outstanding fees', ['ADMIN', 'MANAGER', 'BURSAR', 'HEAD_MASTER'], true],
]
const MONEY = new Set(['Billed', 'Paid', 'Balance'])

export default function Reports() {
  const { user } = useAuth()
  const mine = ALL.filter(([, , roles]) => roles.includes(user.role))
  const [name, setName] = useState(mine[0][0])
  const [branches, setBranches] = useState([])
  const [f, setF] = useState({ branch: '', from: '', to: '' })
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const dated = ALL.find((r) => r[0] === name)[3]
  useEffect(() => { api('/branches/').then((b) => setBranches(user.role === 'HEAD_MASTER' || user.role === 'LIBRARIAN' || user.role === 'ACADEMIC_MASTER' ? b.filter((x) => user.branches.includes(x.id)) : b)) }, [])
  const qs = (extra = '') => '?' + new URLSearchParams(Object.entries({ ...f, ...(dated ? {} : { from: '', to: '' }) }).filter(([, v]) => v)).toString() + extra
  const run = () => { setErr(''); api(`/reports/${name}/${qs()}`).then(setData).catch((e) => { setData(null); setErr(e.message) }) }
  useEffect(run, [name, f.branch, f.from, f.to])

  return (
    <>
      <div className="bar noprint"><h2>Reports</h2></div>
      <div className="tabs noprint">{mine.map(([k, l]) => <button key={k} className={name === k ? 'on' : ''} onClick={() => { if (k !== name) { setData(null); setName(k) } }}>{l}</button>)}</div>
      <div className="line noprint">
        {branches.length > 1 && <select value={f.branch} onChange={(e) => setF({ ...f, branch: e.target.value })}><option value="">All schools</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select>}
        {dated && <><input type="date" title="From" value={f.from} onChange={(e) => setF({ ...f, from: e.target.value })} /><input type="date" title="To" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} /></>}
        <button onClick={() => download(`/reports/${name}/${qs('&export=csv')}`).catch((e) => setErr(e.message))}>Download CSV</button>
        <button onClick={() => window.print()}>Print</button>
      </div>
      {err && <p className="error">{err}</p>}
      {data && (
        <section className="card">
          <h3>{data.title} <span className="muted">· {data.generated}</span></h3>
          <p>{Object.entries(data.summary).map(([k, v]) => <span className="pill" key={k}>{k.replace(/_/g, ' ')}: {['billed', 'collected', 'outstanding'].includes(k) ? tzs(v) : v}</span>)}</p>
          <table><thead><tr>{data.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>{data.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{MONEY.has(data.columns[j]) ? tzs(c) : c === 'LOW' ? <b className="error">LOW</b> : String(c)}</td>)}</tr>)}</tbody></table>
          {data.rows.length === 0 && <p className="muted">Nothing to report for these filters.</p>}
        </section>)}
    </>
  )
}

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { BranchPicker, tzs, useBranches, useLoad } from '../hooks'

export default function Fees() {
  const { user } = useAuth()
  const finance = ['ADMIN', 'BURSAR'].includes(user.role)
  const b = useBranches()
  const [fees, reloadF] = useLoad('/fees/')
  const [inv, reloadI] = useLoad(b.branch ? `/invoices/?branch=${b.branch}&unpaid=1` : '', [b.branch])
  const [rooms] = useLoad(b.branch ? `/classes/?branch=${b.branch}` : '', [b.branch])
  const [f, setF] = useState({ name: '', amount: '', classroom: '', due_date: '' })
  const [pay, setPay] = useState(null)
  const [msg, setMsg] = useState(null)
  const run = async (fn, ok) => { setMsg(null); try { await fn(); setMsg({ ok }) } catch (x) { setMsg({ err: x.message }) } }
  const create = (e) => { e.preventDefault(); run(async () => {
    await api('/fees/', { method: 'POST', body: { ...f, branch: b.branch, amount: f.amount, classroom: f.classroom || null, due_date: f.due_date || null } })
    setF({ name: '', amount: '', classroom: '', due_date: '' }); reloadF() }, 'Fee created. Now press "Bill students".') }
  const generate = (id) => run(async () => { const r = await api(`/fees/${id}/generate/`, { method: 'POST' }); reloadF(); reloadI(); setMsg({ ok: `${r.created} new invoices.` }) })
  const receive = (e) => { e.preventDefault(); run(async () => {
    await api(`/invoices/${pay.id}/pay/`, { method: 'POST', body: { amount: pay.amount, method: pay.method, reference: pay.reference } }); setPay(null); reloadI() }, 'Payment recorded.') }
  const owed = (inv || []).reduce((n, i) => n + +i.balance, 0)
  return (
    <>
      <div className="bar"><h2>Fees</h2><BranchPicker {...b} /></div>
      {msg?.err && <p className="error">{msg.err}</p>}{msg?.ok && <p className="ok">{msg.ok}</p>}
      {finance && (
        <form className="card" onSubmit={create}><h3>New fee</h3><div className="line">
          <input required placeholder="e.g. School fees Term 1" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <input required type="number" min="1" placeholder="Amount (TZS)" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />
          <select value={f.classroom} onChange={(e) => setF({ ...f, classroom: e.target.value })}><option value="">Whole school</option>{(rooms || []).map((r) => <option key={r.id} value={r.id}>{r.name} only</option>)}</select>
          <input type="date" title="Due date" value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })} />
          <button className="primary">Create</button></div></form>)}
      <section className="card"><h3>Fee structure</h3>
        <table><thead><tr><th>School</th><th>Fee</th><th>Applies to</th><th>Amount</th><th>Billed</th><th></th></tr></thead>
          <tbody>{(fees || []).map((x) => <tr key={x.id}><td>{x.branch_name}</td><td>{x.name}</td><td>{x.class_name || 'Whole school'}</td><td>{tzs(x.amount)}</td><td>{x.invoiced}</td>
            <td>{finance && <button className="link" onClick={() => generate(x.id)}>Bill students</button>}</td></tr>)}</tbody></table></section>
      {pay && (
        <form className="card action" onSubmit={receive}><h3>Receive payment — {pay.student_name}</h3><div className="line">
          <input required type="number" min="1" max={pay.balance} value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} />
          <select value={pay.method} onChange={(e) => setPay({ ...pay, method: e.target.value })}><option value="CASH">Cash</option><option value="BANK">Bank</option><option value="MOBILE">Mobile money</option></select>
          <input placeholder="Reference (optional)" value={pay.reference} onChange={(e) => setPay({ ...pay, reference: e.target.value })} />
          <button className="primary">Record</button><button type="button" onClick={() => setPay(null)}>Cancel</button></div></form>)}
      <section className="card"><h3>Outstanding balances <span className="muted">— {tzs(owed)} owed</span></h3>
        <table><thead><tr><th>Student</th><th>Fee</th><th>Amount</th><th>Paid</th><th>Balance</th><th></th></tr></thead>
          <tbody>{(inv || []).map((i) => <tr key={i.id}><td><Link to={`/students/${i.student}`}>{i.student_name}</Link> <span className="muted">{i.admission_no}</span></td><td>{i.fee_name}</td><td>{tzs(i.amount)}</td><td>{tzs(i.paid)}</td><td className="error">{tzs(i.balance)}</td>
            <td>{user.role === 'BURSAR' && <button className="link" onClick={() => setPay({ id: i.id, student_name: i.student_name, balance: i.balance, amount: i.balance, method: 'CASH', reference: '' })}>Receive</button>}</td></tr>)}</tbody></table>
        {inv && inv.length === 0 && <p className="muted">Nobody owes anything.</p>}</section>
    </>
  )
}

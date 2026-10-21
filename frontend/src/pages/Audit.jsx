import { useEffect, useState } from 'react'
import { api, fmt } from '../api'

export default function Audit() {
  const [rows, setRows] = useState([])
  useEffect(() => { api('/audit/').then(setRows) }, [])
  return (
    <>
      <h2>Audit trail</h2>
      <section className="card"><table><thead><tr><th>When</th><th>Who</th><th>Action</th><th>What</th><th>School</th><th>Detail</th></tr></thead>
        <tbody>{rows.map((a) => <tr key={a.id}><td>{fmt(a.created_at)}</td><td>{a.actor_name}</td><td className="mono">{a.action}</td>
          <td>{a.entity} #{a.entity_id}</td><td>{a.branch_name || '—'}</td><td className="muted">{a.detail}</td></tr>)}</tbody></table></section>
    </>
  )
}

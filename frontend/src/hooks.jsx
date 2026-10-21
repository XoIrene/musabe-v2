import { useEffect, useState } from 'react'
import { api } from './api'
import { useAuth } from './auth'

export const MANAGERS = ['ADMIN', 'HEAD_MASTER', 'ACADEMIC_MASTER']          // register students, set up classes and terms
export const SCHOOL_STAFF = ['HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN', 'STAFF']
export const tzs = (n) => 'TZS ' + Number(n || 0).toLocaleString('en-GB', { maximumFractionDigits: 0 })

// The schools this user can work in, plus the one currently selected.
export function useBranches() {
  const { user } = useAuth()
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  useEffect(() => {
    api('/branches/').then((b) => {
      const mine = user.role === 'ADMIN' || user.role === 'MANAGER' || user.role === 'BURSAR' || user.role === 'STOREKEEPER' ? b : b.filter((x) => user.branches.includes(x.id))
      setBranches(mine); if (mine[0]) setBranch(mine[0].id)
    })
  }, [])
  return { branches, branch, setBranch: (v) => setBranch(+v) }
}

export function BranchPicker({ branches, branch, setBranch }) {
  if (branches.length < 2) return null
  return <select value={branch} onChange={(e) => setBranch(e.target.value)}>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
}

export function useLoad(path, deps = []) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const reload = () => api(path).then((d) => { setData(d); setErr('') }).catch((e) => setErr(e.message))
  useEffect(() => { if (path) reload() }, [path, ...deps])
  return [data, reload, err]
}

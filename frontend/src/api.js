// Thin fetch wrapper: adds the JWT, returns JSON, throws readable errors.
const read = (store) => { try { return store.getItem('access') || '' } catch { return '' } }
let token = read(localStorage) || read(sessionStorage)

// "Remember me" keeps the sign-in across browser restarts; otherwise it ends when the tab is closed.
export const setToken = (t, remember = true) => {
  token = t || ''
  try {
    localStorage.removeItem('access'); sessionStorage.removeItem('access')
    if (t) (remember ? localStorage : sessionStorage).setItem('access', t)
  } catch { /* storage blocked: the sign-in lasts until the page reloads */ }
}
export const hasStoredToken = () => !!token

const flatten = (e) =>
  typeof e === 'string' ? e
  : Array.isArray(e) ? e.map(flatten).join(' ')
  : e && typeof e === 'object' ? Object.entries(e).map(([k, v]) => (k === 'detail' || k === 'non_field_errors' ? '' : k + ': ') + flatten(v)).join(' · ')
  : String(e)

export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch('/api' + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401 && token) { setToken(''); location.href = '/login' }
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new Error(flatten(data) || res.statusText)
  return data
}

export const fmt = (d) => d && new Date(d).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })

export const STATUS = {
  PENDING_ACADEMIC: 'Waiting: Academic Master', PENDING_HEAD: 'Waiting: Head Master', PENDING_APPROVAL: 'Waiting: Academic / Head Master',
  PENDING_REQUISITION: 'Waiting: Librarian (requisition)', PENDING_LIBRARIAN: 'Waiting: Librarian', PENDING_PO: 'Waiting: Bursar (PO)',
  PENDING_BURSAR: 'Waiting: Bursar', PENDING_MANAGER: 'Waiting: Manager', PENDING_ORDER: 'Waiting: Storekeeper (order)',
  ORDERED: 'Ordered, awaiting delivery', DELIVERED: 'Delivered, requestor to verify', VERIFIED: 'Verified, Bursar to pay',
  PAID: 'Paid, Storekeeper to send', DISPATCHED: 'Sent, Librarian to receive', COMPLETED: 'Completed', REJECTED: 'Rejected',
}
export const CATEGORIES = { BOOK: 'Book', STATIONERY: 'Stationery', UNIFORM: 'Uniform', FABRIC: 'Sewing material (vitambaa)', PRIMARY: 'Primary School item', OTHER: 'Other' }

// Download a file from the API (the token must travel in a header, so a plain link would not work).
export async function download(path) {
  const res = await fetch('/api' + path, { headers: token ? { Authorization: 'Bearer ' + token } : {} })
  if (!res.ok) throw new Error('Download failed (' + res.status + ')')
  const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '')?.[1] || 'report.csv'
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
}

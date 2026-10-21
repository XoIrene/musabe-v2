import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Requests from './pages/Requests'
import NewRequest from './pages/NewRequest'
import RequestDetail from './pages/RequestDetail'
import Inventory from './pages/Inventory'
import Issuing from './pages/Issuing'
import WriteOffs from './pages/WriteOffs'
import Contributions from './pages/Contributions'
import Admin from './pages/Admin'
import Audit from './pages/Audit'
import Students from './pages/Students'
import StudentDetail from './pages/StudentDetail'
import Classes from './pages/Classes'
import Academics from './pages/Academics'
import Fees from './pages/Fees'
import Transport from './pages/Transport'
import Announcements from './pages/Announcements'
import ParentHome from './pages/ParentHome'
import Reports from './pages/Reports'

// Which roles see which menu entries (the API enforces the same rules).
const ALL = ['ADMIN', 'MANAGER', 'BURSAR', 'STOREKEEPER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN', 'STAFF']
const WITH_PARENTS = [...ALL, 'PARENT']
const STOCK = ALL.filter((r) => r !== 'STAFF')
const SCHOOLWIDE = ['ADMIN', 'MANAGER', 'BURSAR', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN', 'STAFF']
const MENU = [
  ['/', 'Dashboard', ALL, Dashboard, true],
  ['/', 'My children', ['PARENT'], ParentHome, true],
  ['/requests', 'Requests', ALL, Requests],
  ['/inventory', 'Library & Store', STOCK, Inventory],
  ['/issuing', 'Issuing', ['LIBRARIAN', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'ADMIN', 'MANAGER'], Issuing],
  ['/writeoffs', 'Write-offs', ['LIBRARIAN', 'HEAD_MASTER', 'ADMIN', 'MANAGER'], WriteOffs],
  ['/contributions', 'Parent gifts', ['LIBRARIAN', 'HEAD_MASTER'], Contributions],
  ['/students', 'Students', [...SCHOOLWIDE, 'PARENT'], Students],
  ['/classes', 'Classes', SCHOOLWIDE, Classes],
  ['/academics', 'Academics', ['ADMIN', 'MANAGER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'STAFF'], Academics],
  ['/fees', 'Fees', ['ADMIN', 'MANAGER', 'BURSAR', 'HEAD_MASTER'], Fees],
  ['/transport', 'Transport', SCHOOLWIDE, Transport],
  ['/announcements', 'Announcements', WITH_PARENTS, Announcements],
  ['/reports', 'Reports', ['ADMIN', 'MANAGER', 'BURSAR', 'STOREKEEPER', 'HEAD_MASTER', 'ACADEMIC_MASTER', 'LIBRARIAN'], Reports],
  ['/admin', 'Branches & Staff', ['ADMIN'], Admin],
  ['/audit', 'Audit trail', ['ADMIN', 'MANAGER', 'HEAD_MASTER'], Audit],
]

// Small line icons for the sidebar (Feather-style paths).
const P = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  repeat: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
  gift: '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  award: '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
  dollar: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  truck: '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  sliders: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
}
const Icon = ({ name }) => (
  <svg className="icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: P[name] }} />
)
const ICON = { '/': 'home', '/requests': 'list', '/inventory': 'book', '/issuing': 'repeat', '/writeoffs': 'trash', '/contributions': 'gift',
  '/students': 'users', '/classes': 'grid', '/academics': 'award', '/fees': 'dollar', '/transport': 'truck', '/announcements': 'bell',
  '/reports': 'chart', '/admin': 'sliders', '/audit': 'shield' }

export default function App() {
  const { user, ready, logout } = useAuth()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)          // only used on phones; on larger screens the rail expands on hover
  useEffect(() => setOpen(false), [pathname])
  if (!ready) return <p className="center">Loading…</p>
  if (!user) return <Routes><Route path="*" element={<Login />} /></Routes>
  const mine = MENU.filter(([, , roles]) => roles.includes(user.role))
  const here = mine.find(([to]) => to !== '/' && pathname.startsWith(to))
  const crumbs = pathname === '/' ? [] : [here ? here[1] : null, pathname.split('/').length > 2 ? (pathname.endsWith('/new') ? 'New' : 'Details') : null].filter(Boolean)
  return (
    <div className={'shell' + (open ? ' open' : '')}>
      <aside>
        <div className="brand"><img className="logo" src="/logo.png" alt="Musabe Schools" /><h1>Musabe<span> Schools</span></h1></div>
        <nav>{mine.map(([to, label, , , end]) => (
          <NavLink key={to + label} to={to} end={end} title={label}><Icon name={ICON[to]} /><span>{label}</span></NavLink>))}</nav>
        <button className="signout" onClick={logout} title="Sign out"><Icon name="logout" /><span>Sign out</span></button>
      </aside>
      <div className="content">
        <header className="topbar noprint">
          <button className="burger" onClick={() => setOpen(!open)} aria-label="Toggle menu"><Icon name="menu" /></button>
          <span className="crumbs">Home{crumbs.map((c) => <span key={c}> <i>›</i> {c}</span>)}</span>
          <span className="me"><strong>{user.full_name}</strong><small>{user.role_label} · {user.branch_names.join(', ') || 'Central Administration'}</small></span>
        </header>
        <main>
          <Routes>
            {mine.map(([to, , , El]) => <Route key={to} path={to} element={<El />} />)}
            <Route path="/students/:id" element={<StudentDetail />} />
            <Route path="/requests/new" element={<NewRequest />} />
            <Route path="/requests/:id" element={<RequestDetail />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

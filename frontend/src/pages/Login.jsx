import { useState } from 'react'
import { useAuth } from '../auth'

const Mail = () => <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M22 7l-10 6L2 7" /></svg>
const Eye = ({ off }) => <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" /><circle cx="12" cy="12" r="3" />{off && <line x1="3" y1="3" x2="21" y2="21" />}</svg>

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [remember, setRemember] = useState(false)
  const [help, setHelp] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await login(email.trim(), password, remember) }
    catch (x) { setErr(/No active account/.test(x.message) ? 'Wrong email or password.' : 'Cannot reach the server: ' + (x.message || 'please try again.')); setBusy(false) }
  }
  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <header>
          <h1>MUSABE SCHOOLS</h1>
          <img src="/logo.png" alt="Musabe Schools — Education First" />
          <strong>Management System</strong>
        </header>
        <div className="login-body">
          <div className="input-group"><input type="email" required autoFocus placeholder="Email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /><span className="addon"><Mail /></span></div>
          <div className="input-group"><input type={show ? 'text' : 'password'} required placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="button" className="addon" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'}><Eye off={!show} /></button></div>
          <div className="login-row">
            <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /><b>Remember me</b></label>
            <button type="button" className="link" onClick={() => setHelp(!help)}>Forgot password?</button>
          </div>
          {help && <p className="login-help">Passwords are reset by the Admin. Please contact Central Administration and ask for a new one.</p>}
          {err && <p className="error">{err}</p>}
          <button className="primary signin" disabled={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
          <div className="or"><span>Don't have an account?</span></div>
          <p className="login-note">Accounts are created by the Admin in Central Administration.</p>
        </div>
      </form>
      <small className="login-foot">© {new Date().getFullYear()} Musabe Schools · Buhongwa, Mwanza</small>
    </div>
  )
}

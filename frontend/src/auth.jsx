import { createContext, useContext, useEffect, useState } from 'react'
import { api, hasStoredToken, setToken } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!hasStoredToken()) return setReady(true)
    api('/me/').then(setUser).catch(() => setToken('')).finally(() => setReady(true))
  }, [])

  const login = async (email, password, remember = true) => {
    const d = await api('/auth/login/', { method: 'POST', body: { email, password } })
    setToken(d.access, remember); setUser(d.user)
  }
  const logout = () => { setToken(''); setUser(null) }

  return <Ctx.Provider value={{ user, ready, login, logout }}>{children}</Ctx.Provider>
}

/**
 * Minimal auth store — no Redux, plain JS module + React context.
 */
import { createContext, useContext, useState, useCallback } from 'react'
import { login as apiLogin } from '../services/api'

export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export function useAuthProvider() {
  const stored = localStorage.getItem('user')
  const [user, setUser] = useState(stored ? JSON.parse(stored) : null)

  const signIn = useCallback(async (username, password) => {
    const { data } = await apiLogin(username, password)
    const u = {
      username: data.username,
      role: data.role,
      state: data.state,
      district: data.district,
      token: data.access_token,
    }
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(u))
    setUser(u)
    return u
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }, [])

  return { user, signIn, signOut }
}

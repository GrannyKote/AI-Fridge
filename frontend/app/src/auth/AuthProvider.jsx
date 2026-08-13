import { useCallback, useMemo, useState } from 'react'
import { authApi } from '../api/client.js'
import { AuthContext } from './authContext.js'
import { clearSession, readSession, writeSession } from './sessionStore.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readSession)

  const signIn = useCallback(async (login, password) => {
    const account = await authApi.login(login, password)
    writeSession(account)
    setUser(account)
    return account
  }, [])

  const signUp = useCallback(async (login, password) => {
    const account = await authApi.register(login, password)
    writeSession(account)
    setUser(account)
    return account
  }, [])

  const signOut = useCallback(() => {
    clearSession()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), signIn, signUp, signOut }),
    [user, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

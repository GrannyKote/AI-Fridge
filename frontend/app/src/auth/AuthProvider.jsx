import { useCallback, useEffect, useMemo, useState } from 'react'
import { authApi, setUnauthorizedHandler, startOfflineSync } from '../api/client.js'
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

  // Бэкенд ответил 401 — токен устарел, возвращаем пользователя на вход.
  useEffect(() => {
    setUnauthorizedHandler(signOut)
    return () => setUnauthorizedHandler(null)
  }, [signOut])

  useEffect(() => startOfflineSync(user), [user])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isAdmin: Boolean(user?.is_admin),
      signIn,
      signUp,
      signOut,
    }),
    [user, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

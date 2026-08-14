import { useCallback, useMemo, useState } from 'react'
import { ThemeContext } from './themeContext.js'
import { applyTheme, readTheme, writeTheme } from './themeStore.js'

applyTheme(readTheme())

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(readTheme)

  const setDark = useCallback((dark) => {
    const next = dark ? 'dark' : 'light'
    writeTheme(next)
    setTheme(next)
  }, [])

  const value = useMemo(
    () => ({
      theme,
      isDark: theme === 'dark',
      setDark,
    }),
    [theme, setDark],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

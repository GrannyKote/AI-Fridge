const STORAGE_KEY = 'ai-fridge-theme'

export function readTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function applyTheme(theme) {
  const next = theme === 'light' ? 'light' : 'dark'
  document.documentElement.dataset.theme = next
  document.documentElement.style.colorScheme = next

  const color = document.querySelector('meta[name="theme-color"]')
  if (color) {
    color.setAttribute('content', next === 'light' ? '#f3f5f3' : '#0b0c0b')
  }

  const scheme = document.querySelector('meta[name="color-scheme"]')
  if (scheme) {
    scheme.setAttribute('content', next)
  }
}

export function writeTheme(theme) {
  const next = theme === 'light' ? 'light' : 'dark'

  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // localStorage может быть недоступен в приватном режиме
  }

  applyTheme(next)
}

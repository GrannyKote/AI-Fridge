const SESSION_KEY = 'ai-fridge:session'

export function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    const session = raw ? JSON.parse(raw) : null
    return session?.login ? session : null
  } catch {
    return null
  }
}

export function writeSession(user) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(user))
  } catch {
    // приватный режим браузера — сессия просто не переживёт перезагрузку
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    // нечего очищать
  }
}

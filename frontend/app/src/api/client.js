const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

function extractMessage(payload, fallback) {
  const detail = payload?.detail

  if (typeof detail === 'string') {
    return detail
  }

  // Ошибка валидации FastAPI приходит списком объектов.
  if (Array.isArray(detail) && detail[0]?.msg) {
    return detail[0].msg
  }

  return fallback
}

async function post(path, body) {
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('Сервер недоступен. Проверьте, что бэкенд запущен')
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractMessage(payload, 'Не удалось выполнить запрос'))
  }

  return payload
}

export const authApi = {
  register: (login, password) => post('/auth/register', { login, password }),
  login: (login, password) => post('/auth/login', { login, password }),
}

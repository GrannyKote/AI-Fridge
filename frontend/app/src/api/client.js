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

async function request(path, { method = 'GET', body } = {}) {
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Сервер недоступен. Проверьте, что бэкенд запущен')
  }

  if (response.status === 204) {
    return null
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractMessage(payload, 'Не удалось выполнить запрос'))
  }

  return payload
}

async function requestForm(path, body) {
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, { method: 'POST', body })
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
  register: (login, password) =>
    request('/auth/register', {
      method: 'POST',
      body: { login, password, user_agent: navigator.userAgent },
    }),
  login: (login, password) =>
    request('/auth/login', {
      method: 'POST',
      body: { login, password, user_agent: navigator.userAgent },
    }),
}

export const pantryApi = {
  categories: () => request('/categories'),
  places: () => request('/places'),
  units: () => request('/units'),
  searchProducts: (query) =>
    request(`/products/search?query=${encodeURIComponent(query)}&limit=5`),
  shelfLife: (name) =>
    request(`/products/shelf-life?name=${encodeURIComponent(name)}`),
  rememberShelfLife: (name, days) =>
    request('/products/shelf-life', {
      method: 'PUT',
      body: { name, shelf_life_days: days },
    }),
  products: (groupId) => request(`/groups/${groupId}/products`),
  usage: (groupId, period) => request(`/groups/${groupId}/usage?period=${period}`),
  addProduct: (groupId, payload) =>
    request(`/groups/${groupId}/products`, { method: 'POST', body: payload }),
  consumeProduct: (groupId, itemId, quantity) =>
    request(`/groups/${groupId}/products/${itemId}/consumption`, {
      method: 'POST',
      body: { quantity },
    }),
  wasteProduct: (groupId, itemId, payload) =>
    request(`/groups/${groupId}/products/${itemId}/waste`, {
      method: 'POST',
      body: payload,
    }),
}

export const feedbackApi = {
  send: (userId, message, photos) => {
    const body = new FormData()
    body.append('user_id', String(userId))
    body.append('message', message)
    for (const photo of photos) {
      body.append('photos', photo)
    }
    return requestForm('/feedback', body)
  },
  list: (userId) => request(`/feedback?user_id=${userId}`),
  photoUrl: (feedbackId, photoId) => `${BASE_URL}/feedback/${feedbackId}/photos/${photoId}`,
}

export const shoppingApi = {
  list: (groupId) => request(`/groups/${groupId}/purchases`),
  header: (groupId) => request(`/groups/${groupId}/purchase`),
  add: (groupId, payload) =>
    request(`/groups/${groupId}/purchases`, { method: 'POST', body: payload }),
  remove: (groupId, itemId) =>
    request(`/groups/${groupId}/purchases/${itemId}`, { method: 'DELETE' }),
  setPlanDate: (groupId, planDate) =>
    request(`/groups/${groupId}/purchase/plan`, {
      method: 'PATCH',
      body: { plan_date: planDate },
    }),
  checkout: (groupId, items) =>
    request(`/groups/${groupId}/purchase/checkout`, { method: 'POST', body: { items } }),
}

async function recognize(groupId, file, kind) {
  const body = new FormData()
  body.append('file', file)
  const path = kind === 'voice' ? 'asr' : 'ocr'

  let response
  try {
    response = await fetch(`/ml/groups/${groupId}/${path}`, { method: 'POST', body })
  } catch {
    throw new Error('Сервис чеков недоступен')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(extractMessage(payload, 'Не удалось прочитать чек'))
  }
  return payload
}

export const receiptApi = {
  recognize,
}

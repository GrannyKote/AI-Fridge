import { readSession } from '../auth/sessionStore.js'
import { createOfflineRequest } from './offlineStore.js'

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

// Токен просрочен или подделан — сообщаем об этом приложению, чтобы оно разлогинило.
let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

function headers(body, token) {
  return {
    ...(body ? { 'Content-Type': 'application/json' } : null),
    ...(token ? { Authorization: `Bearer ${token}` } : null),
  }
}

const RETRYABLE_STATUSES = new Set([502, 503, 504])
const MAX_GET_ATTEMPTS = 3

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

async function send(path, {
  method = 'GET', body, form, attempt = 0, token = readSession()?.token,
  background = false, operationId,
} = {}) {
  const options = { method, body, form, token, background, operationId }
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        ...headers(form ? null : body, token),
        ...(operationId ? { 'Idempotency-Key': operationId } : {}),
      },
      body: form ?? (body ? JSON.stringify(body) : undefined),
      signal: background ? AbortSignal.timeout(operationId ? 30000 : 10000) : undefined,
    })
  } catch {
    if (!background && method === 'GET' && attempt + 1 < MAX_GET_ATTEMPTS) {
      await wait(300 * (attempt + 1))
      return send(path, { ...options, attempt: attempt + 1 })
    }
    throw Object.assign(new Error('Сервер недоступен. Проверьте подключение'), { transient: true })
  }

  if (response.status === 204) {
    return null
  }

  const payload = await response.json().catch(() => null)

  if (response.status === 401 && token && !background) {
    unauthorizedHandler?.()
  }

  if (!response.ok) {
    if (
      !background && method === 'GET' &&
      RETRYABLE_STATUSES.has(response.status) &&
      attempt + 1 < MAX_GET_ATTEMPTS
    ) {
      await wait(300 * (attempt + 1))
      return send(path, { ...options, attempt: attempt + 1 })
    }
    throw Object.assign(new Error(extractMessage(payload, 'Не удалось выполнить запрос')), {
      status: response.status,
      transient: response.status >= 500 || response.status === 429,
    })
  }

  return payload
}

const { request, start, synchronize } = createOfflineRequest(send)
export { start as startOfflineSync, synchronize as synchronizeOffline }

export function prepareOffline(user) {
  const paths = ['/categories', '/units', '/places']
  for (const { id } of user.groups ?? []) {
    for (const resource of ['products', 'purchases', 'purchase', 'reminders']) {
      paths.push(`/groups/${id}/${resource}`)
    }
  }
  return Promise.all(paths.map((path) => request(path)))
}

async function fetchBlob(path) {
  const token = readSession()?.token
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
  } catch {
    throw new Error('Сервер недоступен. Проверьте, что бэкенд запущен')
  }

  if (response.status === 401 && token) {
    unauthorizedHandler?.()
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(extractMessage(payload, 'Не удалось выполнить запрос'))
  }

  return response.blob()
}

function filenameFromDisposition(header) {
  if (!header) {
    return null
  }
  const match = /filename="([^"]+)"/.exec(header)
  return match?.[1] ?? null
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
  searchProducts: (query, limit = 12) =>
    request(`/products/search?query=${encodeURIComponent(query)}&limit=${limit}`),
  products: (groupId) => request(`/groups/${groupId}/products`),
  reminders: (groupId) => request(`/groups/${groupId}/reminders`),
  markRemindersSeen: (groupId) =>
    request(`/groups/${groupId}/reminders/seen`, { method: 'POST' }),
  usage: (groupId, period) => request(`/groups/${groupId}/usage?period=${period}`),
  addProduct: (groupId, payload, localPlaceId) =>
    request(`/groups/${groupId}/products`, {
      method: 'POST', body: payload,
      localBody: { ...payload, storage_place_id: payload.storage_place_id ?? localPlaceId },
    }),
  updateProduct: (groupId, itemId, payload, localPlaceId) =>
    request(`/groups/${groupId}/products/${itemId}`, {
      method: 'PATCH', body: payload,
      localBody: { ...payload, storage_place_id: payload.storage_place_id ?? localPlaceId },
    }),
  moveProducts: (groupId, payload) =>
    request(`/groups/${groupId}/products/move`, { method: 'POST', body: payload }),
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

export const newsApi = {
  list: () => request('/news'),
  markSeen: (newsId) => request(`/news/${newsId}/seen`, { method: 'POST' }),
  markPersonalSeen: (personalId) =>
    request(`/news/personal/${personalId}/seen`, { method: 'POST' }),
}

export const adminNewsApi = {
  list: () => request('/admin/news'),
  create: (payload) => request('/admin/news', { method: 'POST', body: payload }),
  get: (newsId) => request(`/admin/news/${newsId}`),
  viewers: (newsId) => request(`/admin/news/${newsId}/seen`),
  update: (newsId, payload) =>
    request(`/admin/news/${newsId}`, { method: 'PATCH', body: payload }),
  remove: (newsId) => request(`/admin/news/${newsId}`, { method: 'DELETE' }),
}

export const adminUsersApi = {
  list: () => request('/admin/users'),
  setPassword: (userId, password) =>
    request(`/admin/users/${userId}/password`, { method: 'PATCH', body: { password } }),
}

export const adminFeedbackApi = {
  list: () => request('/admin/feedback'),
  get: (feedbackId) => request(`/admin/feedback/${feedbackId}`),
  reply: (feedbackId, payload) =>
    request(`/admin/feedback/${feedbackId}/reply`, { method: 'POST', body: payload }),
  itemUrl: (feedbackId, itemId, { download = false } = {}) =>
    `${BASE_URL}/admin/feedback/${feedbackId}/items/${itemId}${download ? '?download=1' : ''}`,
  fetchItem: (feedbackId, itemId, options) =>
    fetchBlob(
      `/admin/feedback/${feedbackId}/items/${itemId}${options?.download ? '?download=1' : ''}`,
    ),
  async downloadItem(feedbackId, itemId) {
    const token = readSession()?.token
    const response = await fetch(this.itemUrl(feedbackId, itemId, { download: true }), {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(extractMessage(payload, 'Не удалось скачать изображение'))
    }
    const blob = await response.blob()
    const filename =
      filenameFromDisposition(response.headers.get('Content-Disposition')) ??
      `feedback-${feedbackId}-${itemId}.jpg`
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  },
}

export const feedbackApi = {
  create: (text, files = []) => {
    const form = new FormData()
    form.append('text', text)
    for (const file of files) {
      form.append('images', file)
    }
    return request('/feedback', { method: 'POST', form })
  },
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

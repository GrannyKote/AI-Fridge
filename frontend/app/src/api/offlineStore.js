import { readSession } from '../auth/sessionStore.js'
import { notifyPurchaseChanged } from '../lib/purchaseEvents.js'
import { localChange, project, serverOperation } from './offlineChanges.js'

const PREFIX = 'ai-fridge:data:'
const EVENT = 'ai-fridge:data-status'
const CACHED = /^\/(categories$|places$|units$|products\/search\?|groups\/\d+\/(products$|purchases$|purchase$|reminders$|usage\?))/
const WRITABLE = /^\/groups\/\d+\/(products(?:\/move|\/-?\d+(?:\/(?:consumption|waste))?)?|purchases(?:\/-?\d+)?|purchase\/(?:plan|checkout))$/
const refreshes = new Map()
let notifyTimer
let syncTimer

function accountKey(user) {
  return PREFIX + user.id
}

function read(key) {
  const raw = localStorage.getItem(key)
  return raw ? JSON.parse(raw) : {
    enabled: false, data: {}, queue: [], mapping: {}, nextId: -1, revision: 0, error: '',
  }
}

function notifyDataChanged() {
  clearTimeout(notifyTimer)
  notifyTimer = setTimeout(notifyPurchaseChanged, 30)
}

function write(key, state, changed = false) {
  try {
    localStorage.setItem(key, JSON.stringify(state))
  } catch {
    throw new Error('Не удалось сохранить данные. Проверьте свободное место в браузере')
  }
  window.dispatchEvent(new Event(EVENT))
  if (changed) notifyDataChanged()
}

function lock(name, task) {
  return navigator.locks ? navigator.locks.request(name, async () => task()) : task()
}

function currentAccount(key) {
  const user = readSession()
  return user && accountKey(user) === key ? user : null
}

export function offlineStatus(user) {
  try {
    const state = read(accountKey(user))
    return { enabled: state.enabled, pending: state.queue.length, error: state.error }
  } catch {
    return { enabled: false, pending: 0, error: 'Локальное хранилище недоступно' }
  }
}

export function subscribeOffline(listener) {
  window.addEventListener(EVENT, listener)
  window.addEventListener('storage', listener)
  return () => {
    window.removeEventListener(EVENT, listener)
    window.removeEventListener('storage', listener)
  }
}

export async function changeMode(user, enabled) {
  const key = accountKey(user)
  await lock(key, () => {
    const state = read(key)
    if (!enabled && state.queue.length) {
      throw new Error('Завершите синхронизацию перед переключением режима')
    }
    write(key, {
      ...state,
      enabled,
      data: enabled ? state.data : {},
      error: '',
      revision: state.revision + 1,
    }, true)
  })
}

async function fetchSnapshot(send, path, token) {
  try {
    return await send(path, { token, background: true })
  } catch (error) {
    if (error.status === 404 && /\/purchase$/.test(path)) return null
    throw error
  }
}

function refresh(send, user, path, state) {
  const key = accountKey(user)
  const refreshKey = key + ':' + state.revision + ':' + path
  if (refreshes.has(refreshKey)) return refreshes.get(refreshKey)

  const request = fetchSnapshot(send, path, user.token).then(async (value) => {
    await lock(key, () => {
      const current = read(key)
      if (!currentAccount(key) || !current.enabled || current.revision !== state.revision ||
          current.queue.some((operation) => Object.hasOwn(operation.patch, path))) return
      if (JSON.stringify(current.data[path]) === JSON.stringify(value)) return
      current.data[path] = value
      if (path.startsWith('/products/search?')) {
        const searches = Object.keys(current.data).filter((entry) => entry.startsWith('/products/search?'))
        if (searches.length > 40) delete current.data[searches[0]]
      }
      try {
        // The first caller is already waiting for its initial value.
        write(key, current, Object.hasOwn(state.data, path) && !path.startsWith('/products/search?'))
      } catch {
        // A failed cache write must not prevent reading data from the server.
      }
    })
    return value
  }).finally(() => refreshes.delete(refreshKey))
  refreshes.set(refreshKey, request)
  return request
}

export function createOfflineRequest(send) {
  async function synchronize(user, action) {
    const key = accountKey(user)
    return lock(key + ':sync', async () => {
      if (!currentAccount(key)) return
      if (action) {
        await lock(key, () => {
          const state = read(key)
          if (action === 'discard' && state.error) {
            state.queue = state.queue.filter((operation) => operation.sent)
            state.revision++
            if (!state.queue.length) state.mapping = {}
          }
          state.error = ''
          write(key, state, action === 'discard')
        })
      }
      while (navigator.onLine && currentAccount(key)) {
        const state = read(key)
        if (!state.enabled || !state.queue.length || state.error) return
        const { token } = currentAccount(key)
        const operation = state.queue.find((entry) => !entry.sent)
        let result
        try {
          if (operation) {
            const { path, body } = serverOperation(operation, state.mapping)
            result = await send(path, {
              method: operation.method, body, token, background: true, operationId: operation.id,
            })
            const ids = result?.ids ?? [result?.id]
            if (operation.ids.some((_, index) => !Number.isSafeInteger(ids[index]))) {
              throw Object.assign(new Error('Сервер не подтвердил номера позиций'), { transient: true })
            }
          } else {
            const paths = [...new Set(state.queue.flatMap((entry) => Object.keys(entry.patch)))]
            const values = await Promise.all(paths.map((path) => fetchSnapshot(send, path, token)))
            result = Object.fromEntries(paths.map((path, index) => [path, values[index]]))
          }
        } catch (error) {
          if (!error.transient) {
            await lock(key, () => {
              const current = read(key)
              current.error = error.status === 401 ? 'Войдите снова, чтобы продолжить синхронизацию' : error.message
              write(key, current)
            })
          }
          return
        }
        await lock(key, () => {
          const current = read(key)
          if (operation) {
            const ids = result?.ids ?? [result?.id]
            operation.ids.forEach((id, index) => { current.mapping[id] = ids[index] })
            current.queue.find((entry) => entry.id === operation.id).sent = true
          } else if (current.revision === state.revision) {
            Object.assign(current.data, result)
            current.queue = []
            current.mapping = {}
            current.revision++
          }
          write(key, current, !operation)
        })
      }
    })
  }

  function scheduleSync(user) {
    clearTimeout(syncTimer)
    syncTimer = setTimeout(() => synchronize(user).catch(() => {}), 150)
  }

  function request(path, options = {}) {
    const user = readSession()
    if (!user || user.is_admin) return send(path, options)
    const key = accountKey(user)
    let state
    try {
      state = read(key)
    } catch {
      return send(path, options)
    }
    if (!state.enabled) return send(path, options)
    const { method = 'GET', body, localBody = body } = options
    if (method === 'GET' && CACHED.test(path)) {
      const data = project(state.data, state.queue)
      if (navigator.onLine && !state.queue.some((entry) => Object.hasOwn(entry.patch, path))) {
        const pending = refresh(send, user, path, state)
        if (!Object.hasOwn(data, path)) return pending
        pending.catch(() => {})
      }
      if (Object.hasOwn(data, path)) return Promise.resolve(data[path])
      if (path.startsWith('/products/search?')) {
        const params = new URLSearchParams(path.split('?')[1])
        const query = params.get('query')?.toLowerCase() ?? ''
        const candidates = Object.entries(data)
          .filter(([entry]) => entry.startsWith('/products/search?'))
          .flatMap(([, items]) => items)
          .filter((item) => item.name.toLowerCase().includes(query))
        return Promise.resolve([...new Map(candidates.map((item) => [item.id, item])).values()]
          .slice(0, Number(params.get('limit'))))
      }
      return Promise.reject(new Error('Данные ещё не загружены для работы без сети'))
    }
    if (method === 'GET' || !WRITABLE.test(path)) return send(path, options)

    return lock(key, () => {
      if (!currentAccount(key)) throw new Error('Сессия изменилась. Повторите действие')
      const current = read(key)
      if (!current.enabled) return send(path, options)
      const { patch, ids, nextId, result } = localChange(
        project(current.data, current.queue), path, method, localBody, current.nextId,
      )
      current.queue.push({ id: crypto.randomUUID(), path, method, body, patch, ids })
      current.nextId = nextId
      current.revision++
      write(key, current, true)
      scheduleSync(user)
      return result
    })
  }

  function start(user) {
    if (!user || user.is_admin) return undefined
    function resume() {
      if (offlineStatus(user).pending) scheduleSync(user)
    }
    function reconnect() {
      if (offlineStatus(user).enabled) notifyDataChanged()
      resume()
    }
    function storageChanged(event) {
      if (event.key === accountKey(user)) notifyDataChanged()
    }
    resume()
    window.addEventListener('online', reconnect)
    window.addEventListener('storage', storageChanged)
    const timer = setInterval(resume, 15000)
    return () => {
      window.removeEventListener('online', reconnect)
      window.removeEventListener('storage', storageChanged)
      clearInterval(timer)
    }
  }

  return { request, synchronize, start }
}

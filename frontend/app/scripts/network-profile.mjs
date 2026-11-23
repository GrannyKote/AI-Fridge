import { once } from 'node:events'
import { setTimeout as delay } from 'node:timers/promises'
import { pathToFileURL } from 'node:url'

const bytesPerSecond = (kbps) => kbps * 1000 / 8
const stable = {
  offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1,
}
const slow = {
  offline: false,
  latency: 400,
  downloadThroughput: bytesPerSecond(400),
  uploadThroughput: bytesPerSecond(100),
}
const offline = { ...stable, offline: true }

export const profiles = {
  stable: [{ label: 'Стабильная сеть', conditions: stable }],
  slow: [{ label: 'Медленная сеть', conditions: slow }],
  intermittent: [
    { label: 'Есть связь', conditions: stable, duration: 12000 },
    { label: 'Связь прервана', conditions: offline, duration: 8000 },
  ],
  offline: [{ label: 'Полный оффлайн', conditions: offline }],
}

async function openTab(origin) {
  const response = await fetch('http://127.0.0.1:9222/json/list', {
    signal: AbortSignal.timeout(3000),
  }).catch(() => {
    throw new Error('Запустите Chrome или Edge с портом отладки 9222')
  })
  if (!response.ok) throw new Error(`Порт отладки ответил HTTP ${response.status}`)
  const tabs = (await response.json()).filter(
    (tab) => tab.type === 'page' && new URL(tab.url).origin === origin,
  )
  if (tabs.length !== 1) {
    throw new Error(`Откройте ровно одну вкладку приложения на ${origin} в окне отладки`)
  }
  const socket = new WebSocket(tabs[0].webSocketDebuggerUrl)
  await once(socket, 'open', { signal: AbortSignal.timeout(3000) })
  return socket
}

function networkControl(socket) {
  let nextId = 0
  return (params) => new Promise((resolve, reject) => {
    const id = ++nextId
    const timeout = AbortSignal.timeout(3000)
    function finish(error) {
      socket.removeEventListener('message', onMessage)
      socket.removeEventListener('close', onClose)
      timeout.removeEventListener('abort', onTimeout)
      if (error) reject(error)
      else resolve()
    }
    function onMessage(event) {
      const answer = JSON.parse(event.data)
      if (answer.id === id) finish(answer.error && new Error(answer.error.message))
    }
    const onClose = () => finish(new Error('Вкладка приложения закрылась'))
    const onTimeout = () => finish(new Error('Браузер не подтвердил смену профиля'))
    socket.addEventListener('message', onMessage)
    socket.addEventListener('close', onClose, { once: true })
    timeout.addEventListener('abort', onTimeout, { once: true })
    socket.send(JSON.stringify({ id, method: 'Network.emulateNetworkConditions', params }))
  })
}

async function main(args) {
  const [name, url = 'http://127.0.0.1:5173'] = args
  if (!Object.hasOwn(profiles, name) || args.length > 2) {
    throw new Error('Использование: npm run network:profile -- <stable|slow|intermittent|offline> [URL]')
  }
  const socket = await openTab(new URL(url).origin)
  const apply = networkControl(socket)
  const stop = new AbortController()
  const cancel = () => stop.abort()
  process.once('SIGINT', cancel)
  process.once('SIGTERM', cancel)
  socket.addEventListener('close', cancel, { once: true })

  try {
    while (!stop.signal.aborted) {
      for (const phase of profiles[name]) {
        if (stop.signal.aborted) break
        await apply(phase.conditions)
        console.log(phase.label + (phase.duration ? ` (${phase.duration / 1000} с)` : ' • Ctrl+C для сброса'))
        await delay(phase.duration ?? 2_000_000_000, undefined, { signal: stop.signal })
      }
    }
  } catch (error) {
    if (!stop.signal.aborted) throw error
  } finally {
    try {
      if (socket.readyState === WebSocket.OPEN) await apply(stable)
    } finally {
      socket.close()
      process.removeListener('SIGINT', cancel)
      process.removeListener('SIGTERM', cancel)
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}

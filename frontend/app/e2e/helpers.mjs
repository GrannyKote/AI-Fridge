import { expect } from '@playwright/test'

const measurements = new WeakMap()
export const attachMeasurements = (page) => measurements.get(page)?.()
export const preloadedPantry = process.env.PLAYWRIGHT_PRELOAD_PANTRY === '1'

export async function preloadPantry(page, { guest = false } = {}) {
  await pantryLoaded(page, () => login(page))
  await page.waitForFunction(() => {
    const user = JSON.parse(localStorage.getItem('ai-fridge:session'))
    const data = JSON.parse(localStorage.getItem(`ai-fridge:data:${user.id}`))?.data
    return navigator.serviceWorker.controller && data?.['/categories'] &&
      data['/units'] && data['/places'] && data[`/groups/${user.groups[0].id}/products`]
  }, undefined, { timeout: 15000 })
  const products = await page.evaluate((clearSession) => {
    const user = JSON.parse(localStorage.getItem('ai-fridge:session'))
    const state = JSON.parse(localStorage.getItem(`ai-fridge:data:${user.id}`))
    if (clearSession) localStorage.removeItem('ai-fridge:session')
    return state.data[`/groups/${user.groups[0].id}/products`]
  }, guest)
  await page.context().setOffline(true)
  await page.waitForFunction(() => !navigator.onLine)
  return products
}

export async function openPantry(page, { readProducts = false } = {}) {
  if (preloadedPantry) return preloadPantry(page)
  const response = await pantryLoaded(page, () => login(page))
  if (readProducts) return response.json()
}

export async function waitForOfflineSync(page, testInfo) {
  if (process.env.PLAYWRIGHT_DATA_MODE !== 'offline-first') return
  if (preloadedPantry) {
    const pending = await page.evaluate(() => {
      const user = JSON.parse(localStorage.getItem('ai-fridge:session'))
      const state = JSON.parse(localStorage.getItem(`ai-fridge:data:${user.id}`))
      return state.queue.filter((operation) => !operation.sent).length
    })
    expect(pending).toBe(1)
    await testInfo.attach('offline-queue', {
      body: JSON.stringify({ pending }), contentType: 'application/json',
    })
    return
  }
  const handle = await page.waitForFunction(() => window.playwrightSync, undefined, { timeout: 10000 })
  const outcome = await handle.jsonValue()
  await handle.dispose()
  expect(outcome.error).toBeUndefined()
  expect(outcome.syncMs).toBeGreaterThanOrEqual(0)
  await testInfo.attach('full-sync', {
    body: JSON.stringify(outcome),
    contentType: 'application/json',
  })
}

export function measureRequest(page, testInfo, method, path) {
  const sent = []
  const responses = []
  const statuses = []
  const failures = []
  const matches = (request) => request.method() === method && path.test(new URL(request.url()).pathname)
  page.on('request', (request) => {
    if (matches(request)) sent.push(request)
  })
  page.on('response', (response) => {
    const request = response.request()
    if (matches(request)) {
      statuses.push(response.status())
      const { requestStart, responseStart } = request.timing()
      if (requestStart >= 0 && responseStart >= requestStart) {
        responses.push(responseStart - requestStart)
      }
    }
  })
  page.on('requestfailed', (request) => {
    if (matches(request)) failures.push(request.failure()?.errorText)
  })
  let attached = false
  const attach = async () => {
    if (attached) return
    attached = true
    await testInfo.attach('operation-response', {
      body: JSON.stringify({ requests: sent.length, responseMs: responses[0] ?? null, statuses, failures }),
      contentType: 'application/json',
    })
  }
  measurements.set(page, attach)
  return attach
}

export async function login(page, password = 'demo123') {
  await page.goto('/login')
  await page.getByLabel('Логин').fill('demo')
  await page.getByLabel('Пароль', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Войти', exact: true }).click()
}

export async function pantryLoaded(page, action, acceptsRequest = () => true) {
  const [response] = await Promise.all([
    page.waitForResponse((res) =>
      res.request().method() === 'GET' &&
      /\/api\/groups\/\d+\/products$/.test(new URL(res.url()).pathname) &&
      acceptsRequest(res.request())),
    action(),
  ])
  expect(response.ok()).toBe(true)
  await expect(page.getByText('Загружаем кладовую...', { exact: true })).toBeHidden()
  await expect(page.getByRole('navigation', { name: 'Основная навигация' })
    .getByRole('button', { name: 'Кладовая', exact: true })).toBeVisible()
  return response
}

export async function reloadPantry(page) {
  if (preloadedPantry) {
    const response = await page.reload()
    expect(response?.fromServiceWorker()).toBe(true)
    await expect(page.getByText('Загружаем кладовую...', { exact: true })).toBeHidden()
    await expect(page.getByRole('navigation', { name: 'Основная навигация' })
      .getByRole('button', { name: 'Кладовая', exact: true })).toBeVisible()
    return undefined
  }
  let navigated = false
  const newRequests = new WeakSet()
  const onNavigation = (frame) => {
    if (frame === page.mainFrame()) navigated = true
  }
  const onRequest = (request) => {
    if (navigated) newRequests.add(request)
  }

  // A refresh started by the old document may finish after the reload starts.
  page.on('framenavigated', onNavigation)
  page.on('request', onRequest)
  try {
    return await pantryLoaded(page, () => page.reload(), (request) => newRequests.has(request))
  } finally {
    page.off('request', onRequest)
    page.off('framenavigated', onNavigation)
  }
}

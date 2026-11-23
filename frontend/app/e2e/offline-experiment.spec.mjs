import { randomUUID } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { test } from '@playwright/test'
import { experimentProfiles, networkFor } from './offline-experiment-network.mjs'

const results = fileURLToPath(new URL('../../../research/offline-mvp/trials/', import.meta.url))
const actionTimeout = 6000
const syncWindow = 15000
const expiry = '2027-12-31'
const category = 'Молочные'
const indexes = length => Array.from({ length }, (_, index) => index)
const selectedProfiles = process.env.EXPERIMENT_PROFILE?.split(',') ?? Object.keys(experimentProfiles)
const selectedModes = process.env.EXPERIMENT_MODE?.split(',') ?? ['online-only', 'offline-first']

async function fixture(request) {
  async function api(path, options = {}) {
    const response = await request.fetch('/api' + path, options)
    if (!response.ok()) throw Error(`${options.method ?? 'GET'} ${path}: HTTP ${response.status()} ${await response.text()}`)
    return response.status() === 204 ? null : response.json()
  }

  const user = await api('/auth/register', {
    method: 'POST', data: { login: 'exp' + randomUUID().slice(0, 16).replaceAll('-', ''), password: randomUUID() },
  })
  const group = '/groups/' + user.groups[0].id
  const headers = { Authorization: 'Bearer ' + user.token }
  const call = (path, method = 'GET', data) => api(group + path, { method, headers, data })
  const [units, places] = await Promise.all([api('/units'), api('/places')])
  const fields = { category, unit_id: units.find(x => x.name === 'шт').id, quantity: 1 }
  const pantryFields = { ...fields, best_before: expiry, storage_place_id: places.find(x => x.name === 'Холодильник').id }
  const pantry = []
  const shopping = []
  for (const index of indexes(5)) {
    pantry.push(await call('/products', 'POST', { ...pantryFields, name: 'Остаток ' + (index + 1) }))
  }
  for (const index of indexes(15)) {
    shopping.push(await call('/purchases', 'POST', { ...fields, name: 'Покупка ' + (index + 1) }))
  }
  await call('/purchase/plan', 'PATCH', { plan_date: expiry })
  return { user, group, call, pantry, shopping, pantryFields, headers }
}

async function prepare(page, context, data, mode) {
  await context.addInitScript(({ user, group, enabled }) => {
    localStorage.setItem('ai-fridge:session', JSON.stringify(user))
    const key = 'ai-fridge:data:' + user.id
    if (enabled && !localStorage.getItem(key)) {
      localStorage.setItem(key, JSON.stringify({
        enabled, data: {}, queue: [], mapping: {}, nextId: -1, revision: 0, error: '',
      }))
    }
    window.experimentCacheReady = () => {
      const entries = JSON.parse(localStorage.getItem(key))?.data
      return ['/categories', '/units', '/places', group + '/purchase', group + '/purchases', group + '/products']
        .every(path => Object.hasOwn(entries ?? {}, path))
    }
  }, { user: data.user, group: data.group, enabled: mode === 'offline-first' })
  await page.goto('/')
  await page.getByRole('button', { name: 'Рассчитать', exact: true }).waitFor()
  await page.getByRole('button', { name: 'Рассчитать', exact: true }).click()
  await page.locator('.checkout-card select option').first().waitFor({ state: 'attached' })
  await page.locator('.checkout-card select option:nth-child(2)').first().waitFor({ state: 'attached' })
  await page.getByRole('button', { name: 'Назад', exact: true }).click()
  const pantryPage = await context.newPage()
  await pantryPage.goto('/')
  await pantryPage.getByRole('button', { name: 'Редактировать «Остаток 1»', exact: true }).waitFor()
  if (mode === 'offline-first') await page.waitForFunction(() => window.experimentCacheReady())
  return pantryPage
}

function audit(page, group, requests) {
  const mutations = new Map()
  page.on('request', request => {
    const path = new URL(request.url()).pathname.replace('/api' + group, '')
    if (!((request.method() === 'PATCH' && /^\/products\/\d+$/.test(path)) ||
          (request.method() === 'POST' && path === '/purchase/checkout'))) return
    const entry = { path, key: request.headers()['idempotency-key'] ?? null, status: null, responseAt: null }
    mutations.set(request, entry)
    requests.push(entry)
  })
  page.on('response', response => {
    const entry = mutations.get(response.request())
    if (entry) {
      entry.status = response.status()
      entry.responseAt = performance.now()
    }
  })
}

async function awaitOutcome(success, failure) {
  await success.or(failure).first().waitFor({ timeout: actionTimeout })
  if (await failure.isVisible()) throw Error(await failure.innerText())
}

async function edit(page, item, record) {
  const dialog = page.getByRole('dialog', { name: 'Редактировать продукт' })
  await page.getByRole('button', { name: `Редактировать «${item.name}»`, exact: true }).click({ timeout: actionTimeout })
  try {
    await dialog.getByLabel('Количество', { exact: true }).fill('6', { timeout: actionTimeout })
    await record(async () => {
    await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click({ timeout: actionTimeout })
    await awaitOutcome(page.getByRole('status').filter({ hasText: `«${item.name}» обновлён` }), dialog.getByRole('alert'))
    })
  } finally {
    if (await dialog.isVisible()) {
      await dialog.getByRole('button', { name: 'Назад', exact: true }).click({ timeout: actionTimeout })
    }
    await dialog.waitFor({ state: 'hidden', timeout: actionTimeout })
  }
}

for (const profile of selectedProfiles) {
  for (const mode of selectedModes) {
    test(`offline-experiment ${profile} ${mode}`, async ({ page, context, request }, testInfo) => {
      test.setTimeout(90000)
      const data = await fixture(request)
      const pantryPage = await prepare(page, context, data, mode)
      const apply = await networkFor(page, pantryPage)
      const phases = experimentProfiles[profile]
      const requests = []
      audit(page, data.group, requests)
      audit(pantryPage, data.group, requests)
      const actions = [
        ...data.shopping.map(x => ({ kind: 'mark', id: x.id, name: x.name })),
        ...data.pantry.map(x => ({ kind: 'edit', id: x.id, name: x.name })),
        { kind: 'checkout' },
      ]

      async function record(action, perform) {
        const started = performance.now()
        try {
          await perform()
          action.acceptedAt = performance.now()
          action.uiMs = action.acceptedAt - started
        } catch (error) {
          action.error = String(error.message).split('\n')[0]
        }
      }

      await page.bringToFront()
      await apply(phases.opening)
      const opening = {}
      await record(opening, async () => {
        await page.getByRole('button', { name: 'Покупки', exact: true }).click({ timeout: actionTimeout })
        await awaitOutcome(page.getByText(data.shopping[0].name, { exact: true }), page.getByRole('button', { name: 'Повторить', exact: true }))
        await page.getByRole('button', { name: 'Рассчитать', exact: true }).click({ timeout: actionTimeout })
        await page.locator('.checkout-card select option:nth-child(2)').first().waitFor({ state: 'attached', timeout: actionTimeout })
      })

      if (opening.acceptedAt !== undefined) {
        const dialog = page.getByRole('dialog', { name: 'Рассчитать покупки' })
        // The production dialog defaults to selected. Clear the fixtures before timing the marks.
        for (const item of data.shopping) {
          const name = `Снять «${item.name}»`
          await dialog.getByRole('button', { name, exact: true }).dispatchEvent('click', {}, { timeout: actionTimeout })
        }
        if (phases.marking) await apply(phases.marking)
        for (const action of actions.slice(0, 15)) {
          await record(action, async () => {
            await dialog.getByRole('button', { name: `Отметить «${action.name}»`, exact: true }).dispatchEvent('click', {}, { timeout: actionTimeout })
            await dialog.getByRole('button', { name: `Снять «${action.name}»`, exact: true, pressed: true }).waitFor({ timeout: actionTimeout })
          })
        }

        for (const field of await dialog.getByLabel('Срок годности', { exact: true }).all()) {
          await field.fill('31/12/2027', { timeout: actionTimeout })
        }

        await pantryPage.bringToFront()
        for (const [index, item] of data.pantry.entries()) {
          if (phases.edits) await apply(phases.edits[index])
          const action = actions[index + 15]
          try {
            await edit(pantryPage, item, perform => record(action, perform))
          } catch (error) {
            action.error = String(error.message).split('\n')[0]
          }
        }

        await page.bringToFront()
        if (phases.checkout) await apply(phases.checkout)
        await record(actions.at(-1), async () => {
          await dialog.getByRole('button', { name: 'Добавить', exact: true }).click({ timeout: actionTimeout })
          await awaitOutcome(page.getByRole('status').filter({ hasText: 'В кладовую добавлено: 15' }), dialog.getByRole('alert'))
        })
      }

      const restoredAt = ['intermittent', 'offline'].includes(profile) ? await apply('stable') : performance.now()
      const deadline = restoredAt + syncWindow
      let products
      let purchases
      let checkoutSaved
      const matching = action => products.filter(product => product.name === action.name)
      const correct = action => {
        if (action.kind === 'checkout') return checkoutSaved
        if (action.kind === 'mark') return matching(action).length === 1 && Number(matching(action)[0].remaining) === 1
        return Number(products.find(product => product.id === action.id)?.remaining) === 6
      }
      // Keep observing accepted writes up to the fixed deadline, using the real read handlers.
      do {
        ;[products, purchases] = await Promise.all([data.call('/products'), data.call('/purchases')])
        checkoutSaved = purchases.length === 0 && actions.slice(0, 15).every(correct)
        if (actions.every(action => action.acceptedAt === undefined || correct(action))) break
        await new Promise(resolve => setTimeout(resolve, 50))
      } while (performance.now() < deadline)

      const writes = actions.filter(action => action.kind !== 'mark')
      for (const action of actions) {
        action.applied = correct(action)
        action.success = action.acceptedAt !== undefined && action.applied
        action.duplicate = action.kind === 'mark' && matching(action).length > 1
      }
      const active = writes.filter(action => action.success)
      const responseTimes = active.map(action => requests.find(entry =>
        entry.path === (action.kind === 'checkout' ? '/purchase/checkout' : '/products/' + action.id) &&
        entry.status >= 200 && entry.status < 300)?.responseAt)
      const pending = writes.filter(action => action.acceptedAt !== undefined && !action.applied).length
      const timestamp = active.length > 0 && responseTimes.every(time => time !== undefined)
        ? Math.max(...responseTimes) : null
      const syncMs = pending === 0 && timestamp !== null && ['offline', 'intermittent'].includes(profile)
        ? Math.max(0, timestamp - restoredAt) : null
      const deliveryMs = active.flatMap((action, index) => responseTimes[index] === undefined
        ? [] : [Math.max(0, responseTimes[index] - action.acceptedAt)])
      await mkdir(results, { recursive: true })
      const row = { profile, mode, run: testInfo.repeatEachIndex, group: data.user.groups[0].id,
        opening, actions, requests, losses: pending, syncMs, deliveryMs,
        expectedPurchaseIds: data.shopping.map(item => item.id), userId: data.user.id }
      await writeFile(results + `/${profile}-${mode}-${row.run}.json`, JSON.stringify(row))
    })
  }
}




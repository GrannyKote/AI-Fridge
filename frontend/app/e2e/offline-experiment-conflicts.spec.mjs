import { randomUUID } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { networkFor } from './offline-experiment-network.mjs'

const output = fileURLToPath(new URL('../../../research/offline-mvp/conflicts/', import.meta.url))

for (const scenario of ['same-pantry-item', 'deleted-shopping-item', 'duplicate-delivery']) {
  test(scenario, async ({ page, request }) => {
    test.setTimeout(60000)
    const registration = await request.post('/api/auth/register', {
      data: { login: 'exp' + randomUUID().slice(0, 16).replaceAll('-', ''), password: randomUUID() },
    })
    await expect(registration).toBeOK()
    const user = await registration.json()
    const group = '/groups/' + user.groups[0].id
    const call = (resource, method = 'GET', data, extra = {}) => request.fetch('/api' + group + resource, {
      method, data, headers: { Authorization: 'Bearer ' + user.token, ...extra },
    })
    async function json(response) {
      await expect(response).toBeOK()
      return response.json()
    }

    const units = await json(await request.get('/api/units'))
    const places = await json(await request.get('/api/places'))
    const fields = { name: 'Конфликтный товар', category: 'Молочные', unit_id: units.find(x => x.name === 'шт').id, quantity: 1 }
    const expiry = '2027-12-31'
    const pantryFields = { ...fields, best_before: expiry, storage_place_id: places.find(x => x.name === 'Холодильник').id }
    const result = { scenario }
    if (scenario === 'duplicate-delivery') {
      const product = await json(await call('/purchases', 'POST', fields))
      const payload = { items: [{ id: product.id, quantity: 1, best_before: expiry, storage_place_id: pantryFields.storage_place_id }] }
      const headers = { 'Idempotency-Key': randomUUID() }
      const first = await json(await call('/purchase/checkout', 'POST', payload, headers))
      const repeated = await json(await call('/purchase/checkout', 'POST', payload, headers))
      const changed = await call('/purchase/checkout', 'POST', { items: [{ ...payload.items[0], quantity: 2 }] }, headers)
      const pantry = await json(await call('/products'))
      expect(repeated).toEqual(first)
      expect(changed.status()).toBe(409)
      expect(pantry).toHaveLength(1)
      Object.assign(result, { first, repeated, changedPayloadStatus: changed.status(), pantry })
    } else {
      const path = scenario === 'same-pantry-item' ? '/products' : '/purchases'
      const product = await json(await call(path, 'POST', path === '/products' ? pantryFields : fields))
      if (path === '/purchases') await expect(await call('/purchase/plan', 'PATCH', { plan_date: expiry })).toBeOK()
      await page.addInitScript(account => {
        localStorage.setItem('ai-fridge:session', JSON.stringify(account))
        const key = 'ai-fridge:data:' + account.id
        if (!localStorage.getItem(key)) localStorage.setItem(key, JSON.stringify({
          enabled: true, data: {}, queue: [], mapping: {}, nextId: -1, revision: 0, error: '',
        }))
        window.experimentState = () => JSON.parse(localStorage.getItem(key))
      }, user)
      await page.goto('/')
      const apply = await networkFor(page)
      const snapshot = () => page.evaluate(() => window.experimentState())
      if (path === '/products') {
        await page.getByRole('button', { name: 'Редактировать «Конфликтный товар»' }).click()
        const dialog = page.getByRole('dialog', { name: 'Редактировать продукт' })
        await dialog.getByLabel('Количество', { exact: true }).fill('6')
        await apply('offline')
        await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click()
      } else {
        await page.getByRole('button', { name: 'Рассчитать', exact: true }).click()
        const dialog = page.getByRole('dialog', { name: 'Рассчитать покупки' })
        await dialog.locator('select option:nth-child(2)').first().waitFor({ state: 'attached' })
        await dialog.getByLabel('Срок годности', { exact: true }).fill('31/12/2027')
        await page.waitForFunction(path => Object.hasOwn(window.experimentState().data, path), group + '/products')
        await apply('offline')
        await dialog.getByRole('button', { name: 'Добавить', exact: true }).click()
      }
      await expect.poll(async () => (await snapshot()).queue.length).toBe(1)

      const remote = scenario === 'same-pantry-item'
        ? await call('/products/' + product.id, 'PATCH', { ...pantryFields, quantity: 9 })
        : await call('/purchases/' + product.id, 'DELETE')
      await expect(remote).toBeOK()
      const clientResponse = page.waitForResponse(response =>
        response.request().headers()['idempotency-key'] && response.url().includes('/api' + group + '/'))
      await apply('stable')
      const response = await clientResponse
      const status = response.status()
      if (scenario === 'same-pantry-item') {
        expect(status).toBe(200)
        await expect.poll(async () => (await snapshot()).queue.length).toBe(0)
        const [stored] = await json(await call('/products'))
        expect(Number(stored.remaining)).toBe(6)
        Object.assign(result, { initial: 1, local: 6, remote: 9, status, final: stored.remaining,
          reportedConflict: Boolean((await snapshot()).error) })
      } else {
        expect(status).toBe(422)
        await expect.poll(async () => (await snapshot()).error).toBeTruthy()
        expect(await json(await call('/products'))).toHaveLength(0)
        const pending = await snapshot()
        Object.assign(result, { status, pending: pending.queue.length, userError: pending.error, pantryCount: 0 })
      }
    }
    await mkdir(output, { recursive: true })
    await writeFile(output + '/' + scenario + '.json', JSON.stringify(result, null, 2))
  })
}

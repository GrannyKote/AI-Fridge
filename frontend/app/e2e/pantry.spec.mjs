import { randomUUID } from 'node:crypto'
import { expect } from '@playwright/test'
import { test } from './network.mjs'
import { measureRequest, openPantry, preloadedPantry, reloadPantry, waitForOfflineSync } from './helpers.mjs'

const productName = () => `Тестовый продукт ${randomUUID()}`
const card = (page, name) => page.getByRole('article').filter({
  has: page.getByRole('button', { name: `Редактировать «${name}»`, exact: true }),
})

async function seedProduct(request, quantity) {
  const loginResponse = await request.post('/api/auth/login', {
    data: { login: 'demo', password: 'demo123' },
  })
  await expect(loginResponse).toBeOK()
  const { token, groups } = await loginResponse.json()
  const [units, places] = await Promise.all([request.get('/api/units'), request.get('/api/places')])
  await expect(units).toBeOK()
  await expect(places).toBeOK()
  const unit = (await units.json()).find(({ name }) => name === 'шт')
  const place = (await places.json()).find(({ name }) => name === 'Холодильник')
  const name = productName()
  const response = await request.post(`/api/groups/${groups[0].id}/products`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      name,
      category: 'Молочные',
      unit_id: unit.id,
      quantity,
      best_before: '2027-12-31',
      storage_place_id: place.id,
    },
  })
  await expect(response).toBeOK()
  return (await response.json()).name
}

async function openWaste(page, name) {
  await card(page, name).getByRole('button', { name: `Удалить «${name}»` }).click()
  const dialog = page.getByRole('dialog', { name: 'Списать продукт' })
  await expect(dialog).toBeVisible()
  return dialog
}

test('добавление продукта вручную', async ({ page }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'POST', /^\/api\/groups\/\d+\/products$/)
  const name = productName()
  await openPantry(page)
  await page.getByRole('button', { name: 'Добавить продукт' }).click()
  const dialog = page.getByRole('dialog', { name: 'Добавить продукт' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('tab', { name: 'Вручную' }).click()
  await dialog.getByLabel('Название', { exact: true }).fill(name)
  await dialog.getByLabel('Категория', { exact: true }).selectOption({ label: 'Молочные' })
  await dialog.getByLabel('Единица', { exact: true }).selectOption({ label: 'шт' })
  await dialog.getByLabel('Количество', { exact: true }).fill('4')
  await dialog.getByLabel('Срок годности', { exact: true }).fill('31/12/2027')
  await dialog.getByRole('group', { name: 'Хранение' }).getByRole('button', { name: 'Холодильник' }).click()
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click()

  await expect(page.getByRole('status').filter({ hasText: `«${name}» добавлен` })).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(card(page, name).getByText('4 шт', { exact: true })).toBeVisible()
  await waitForOfflineSync(page, testInfo)
  await measure()
})

test('получение списка, поиск и повторная загрузка', async ({ page, request }, testInfo) => {
  const measure = preloadedPantry ? null : measureRequest(page, testInfo, 'GET', /^\/api\/groups\/\d+\/products$/)
  const name = await seedProduct(request, 4)
  const products = await openPantry(page, { readProducts: true })
  expect(Array.isArray(products)).toBe(true)
  expect(products).toContainEqual(expect.objectContaining({ name }))
  await expect(card(page, name)).toBeVisible()

  const search = page.getByRole('searchbox', { name: 'Поиск продукта' })
  await search.fill(name)
  await expect(page.getByRole('article').filter({
    has: page.getByRole('button', { name: /^Редактировать «/ }),
  })).toHaveCount(1)
  await expect(card(page, name)).toBeVisible()
  await search.clear()
  await search.fill('нет такого продукта')
  await expect(page.getByText('Ничего не нашлось. Попробуйте другой запрос.')).toBeVisible()
  await expect(card(page, name)).toHaveCount(0)

  await reloadPantry(page)
  await expect(card(page, name)).toBeVisible()
  await measure?.()
})

test('редактирование продукта', async ({ page, request }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'PATCH', /^\/api\/groups\/\d+\/products\/\d+$/)
  const name = await seedProduct(request, 4)
  await openPantry(page)
  await card(page, name).getByRole('button', { name: `Редактировать «${name}»` }).click()
  const dialog = page.getByRole('dialog', { name: 'Редактировать продукт' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByLabel('Название', { exact: true })).toHaveValue(name)
  await dialog.getByLabel('Количество', { exact: true }).fill('6')
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: `«${name}» обновлён` })).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(card(page, name).getByText('6 шт', { exact: true })).toBeVisible()
  await waitForOfflineSync(page, testInfo)
  await measure()
})

test('частичное списание', async ({ page, request }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'POST', /^\/api\/groups\/\d+\/products\/\d+\/waste$/)
  const name = await seedProduct(request, 6)
  await openPantry(page)
  const dialog = await openWaste(page, name)
  await expect(dialog.getByText('В наличии: 6 шт', { exact: true })).toBeVisible()
  await expect(dialog.getByRole('radio', { name: 'Продукт испортился' })).toBeChecked()
  await dialog.getByLabel('Количество', { exact: true }).fill('1')
  await dialog.getByRole('button', { name: 'Списать 1 шт', exact: true }).click()

  await expect(page.getByRole('status').filter({ hasText: `Осталось 5 шт «${name}»` })).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(card(page, name).getByText('5 шт', { exact: true })).toBeVisible()
  await waitForOfflineSync(page, testInfo)
  await measure()
})

test('полное списание сохраняется после обновления страницы', async ({ page, request }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'POST', /^\/api\/groups\/\d+\/products\/\d+\/waste$/)
  const name = await seedProduct(request, 5)
  await openPantry(page)
  const dialog = await openWaste(page, name)
  await dialog.getByRole('button', { name: 'Всё 5 шт', exact: true }).click()
  await dialog.getByRole('button', { name: 'Списать 5 шт', exact: true }).click()

  await expect(page.getByRole('status').filter({ hasText: `«${name}» списан полностью` })).toBeVisible()
  await expect(dialog).toBeHidden()
  await expect(card(page, name)).toHaveCount(0)
  await waitForOfflineSync(page, testInfo)
  const response = await reloadPantry(page)
  if (preloadedPantry) await waitForOfflineSync(page, testInfo)
  else expect(await response.json()).not.toContainEqual(expect.objectContaining({ name }))
  await expect(card(page, name)).toHaveCount(0)
  await measure()
})

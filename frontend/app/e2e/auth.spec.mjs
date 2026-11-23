import { expect } from '@playwright/test'
import { test } from './network.mjs'
import { login, measureRequest, preloadedPantry, preloadPantry } from './helpers.mjs'

test.beforeEach(async ({ page }) => {
  if (preloadedPantry) await preloadPantry(page, { guest: true })
})

test('доступ к кладовой без сессии', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Вход' })).toBeVisible()
  await expect(page.getByLabel('Логин')).toBeVisible()
  await expect(page.getByLabel('Пароль', { exact: true })).toBeVisible()
  if (preloadedPantry) return
  const responseMs = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0]
    return navigation.responseStart - navigation.requestStart
  })
  await testInfo.attach('navigation-response', {
    body: JSON.stringify({ responseMs }),
    contentType: 'application/json',
  })
})

test('отправка пустой формы входа', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Войти', exact: true }).click()
  await expect(page.getByText('Введите логин', { exact: true })).toBeVisible()
  await expect(page.getByText('Введите пароль', { exact: true })).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
})

test('вход с неверным паролем', async ({ page }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'POST', /^\/api\/auth\/login$/)
  const [request] = await Promise.all([
    page.waitForRequest((req) => new URL(req.url()).pathname === '/api/auth/login'),
    login(page, 'wrong-password'),
  ])
  expect((await request.response())?.status()).toBe(401)
  await expect(page.getByText('Неверный логин или пароль', { exact: true })).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('button', { name: 'Войти', exact: true })).toBeEnabled()
  expect(await page.evaluate(() => localStorage.getItem('ai-fridge:session'))).toBeNull()
  await measure()
})

test('вход с верными данными', async ({ page }, testInfo) => {
  const measure = measureRequest(page, testInfo, 'POST', /^\/api\/auth\/login$/)
  await login(page)
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('banner').getByRole('heading', { name: 'demo' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Основная навигация' })
    .getByRole('button', { name: 'Кладовая', exact: true })).toHaveAttribute('aria-current', 'page')
  await measure()
})

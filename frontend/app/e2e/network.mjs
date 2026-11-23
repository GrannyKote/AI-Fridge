import { test as base } from '@playwright/test'
import { profiles } from '../scripts/network-profile.mjs'
import { attachMeasurements, preloadedPantry } from './helpers.mjs'

export const test = base.extend({
  page: async ({ page }, runTest, testInfo) => {
    if (process.env.PLAYWRIGHT_DATA_MODE === 'offline-first') {
      const id = Number(process.env.PLAYWRIGHT_DEMO_ID)
      if (!Number.isSafeInteger(id)) throw new Error('Не задан ID пользователя demo')
      await page.addInitScript((accountId) => {
        const key = `ai-fridge:data:${accountId}`
        if (localStorage.getItem(key) === null) {
          localStorage.setItem(key, JSON.stringify({
            enabled: true, data: {}, queue: [], mapping: {}, nextId: -1, revision: 0, error: '',
          }))
        }
        let queuedAt
        window.addEventListener('ai-fridge:data-status', () => {
          if (window.playwrightSync) return
          const state = JSON.parse(localStorage.getItem(key))
          if (state.queue.length && queuedAt === undefined) queuedAt = performance.now()
          if (queuedAt === undefined) return
          if (state.error) window.playwrightSync = { error: state.error }
          else if (!state.queue.length) window.playwrightSync = { syncMs: performance.now() - queuedAt }
        })
      }, id)
    }
    const profile = process.env.PLAYWRIGHT_NETWORK_PROFILE
    if (preloadedPantry) {
      try {
        await runTest(page)
      } finally {
        await attachMeasurements(page)
      }
      return
    }
    if (!profile) {
      await runTest(page)
      return
    }
    const phases = profiles[profile]
    if (!phases) throw new Error(`Неизвестный сетевой профиль Playwright: ${profile}`)
    const session = await page.context().newCDPSession(page)
    let timer
    let transition = Promise.resolve()
    let transitionError
    try {
      const apply = (index) => session.send('Network.emulateNetworkConditions', phases[index].conditions)
      if (phases.length === 1) {
        await apply(0)
      } else {
        const cycle = phases.reduce((sum, phase) => sum + phase.duration, 0)
        const offset = (testInfo.repeatEachIndex % 50) * cycle / 50
        const first = offset < phases[0].duration ? 0 : 1
        const remaining = first === 0 ? phases[0].duration - offset : cycle - offset
        const schedule = (index, duration) => {
          timer = setTimeout(() => {
            transition = apply(index).then(() => {
              schedule((index + 1) % phases.length, phases[index].duration)
            }).catch((error) => { transitionError = error })
          }, duration)
        }
        await apply(first)
        await testInfo.attach('network-start', {
          body: JSON.stringify({ offset, offline: phases[first].conditions.offline }),
          contentType: 'application/json',
        })
        schedule((first + 1) % phases.length, remaining)
      }
      await runTest(page)
    } finally {
      clearTimeout(timer)
      await transition
      clearTimeout(timer)
      await attachMeasurements(page)
      await session.detach()
    }
    if (transitionError) throw transitionError
  },
})

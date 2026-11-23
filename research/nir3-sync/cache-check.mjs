// Run from the repository: node research/nir3-sync/cache-check.mjs
// The production cache module and its imports are unmodified. Only browser I/O is replaced.
import assert from 'node:assert/strict'
import { createOfflineRequest } from '../../frontend/app/src/api/offlineStore.js'

const memory = new Map()
globalThis.localStorage = {
  getItem: key => memory.get(key) ?? null,
  setItem: (key, value) => memory.set(key, value),
}
globalThis.window = new EventTarget()
Object.defineProperty(globalThis, 'navigator', { value: { onLine: true }, configurable: true })
const user = { id: 1, login: 'study', token: 'test-token' }
localStorage.setItem('ai-fridge:session', JSON.stringify(user))
const key = 'ai-fridge:data:1'
const pantry = '/groups/1/products'
const list = '/groups/1/purchases'
const old = { [pantry]: [], [list]: [{ id: 4, name: 'Молоко' }] }
const latest = { [pantry]: [{ id: 8, name: 'Молоко' }], [list]: [] }
const read = () => JSON.parse(localStorage.getItem(key)).data
const tick = () => new Promise(resolve => setImmediate(resolve))

for (const path of [pantry, list]) {
  const other = path === pantry ? list : pantry
  localStorage.setItem(key, JSON.stringify({ enabled: true, data: old, queue: [],
    mapping: {}, nextId: -1, revision: 0, error: '' }))
  const deferred = new Map()
  const { request } = createOfflineRequest(
    target => new Promise(resolve => deferred.set(target, resolve)))
  await Promise.all([request(pantry), request(list)])
  deferred.get(path)(latest[path])
  await tick()
  assert.deepEqual(read()[path], latest[path])
  assert.deepEqual(read()[other], old[other])
  const intermediate = { pantryRows: read()[pantry].length, shoppingRows: read()[list].length }
  deferred.get(other)(latest[other])
  await tick()
  assert.deepEqual(read(), latest)
  console.log(JSON.stringify({ first: path, intermediate, final: 'consistent' }))
}

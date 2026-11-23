function itemRequired(items, id) {
  const item = items.find((entry) => entry.id === id)
  if (!item) throw new Error('Позиция недоступна в локальной копии')
  return item
}

export function project(data, queue) {
  const projected = { ...data }
  for (const { patch } of queue) {
    for (const [path, change] of Object.entries(patch)) {
      if (!change.upsert) {
        projected[path] = change.value
        continue
      }
      const removed = new Set(change.remove)
      const items = new Map(projected[path].filter((item) => !removed.has(item.id))
        .map((item) => [item.id, item]))
      for (const item of change.upsert) items.set(item.id, item)
      projected[path] = [...items.values()]
    }
  }
  return projected
}

export function localChange(data, path, method, body, nextId) {
  const [, root, resource] = path.match(/^(\/groups\/\d+)\/(.+)$/)
  const pantry = root + '/products'
  const purchases = root + '/purchases'
  const header = root + '/purchase'
  const patch = {}
  const ids = []
  let result = null
  const allocate = () => {
    const id = nextId--
    ids.push(id)
    return id
  }
  const list = (key) => {
    if (!data[key]) throw new Error('Сначала загрузите данные при подключении к серверу')
    return data[key]
  }
  const place = (id) => ({
    storage_place_id: id,
    storage_place: data['/places']?.find((item) => item.id === id)?.name ?? null,
  })
  const itemFields = (payload) => ({
    ...payload,
    category_id: data['/categories']?.find((item) => item.name === payload.category)?.id ?? null,
    unit: data['/units']?.find((item) => item.id === payload.unit_id)?.name ?? null,
  })

  if (resource === 'products') {
    result = {
      ...itemFields(body),
      ...place(body.storage_place_id),
      id: allocate(),
      remaining: body.quantity,
    }
    patch[pantry] = [...list(pantry), result]
  } else if (resource === 'purchases') {
    result = { ...itemFields(body), id: allocate() }
    patch[purchases] = [...list(purchases), result]
  } else if (resource === 'purchase/plan') {
    result = { ...data[header], plan_date: body.plan_date }
    patch[header] = result
  } else if (resource === 'purchase/checkout') {
    const items = list(purchases)
    const added = body.items.map(({ id, ...fields }) => {
      const purchase = itemRequired(items, id)
      const unit = data['/units']?.find((entry) => entry.name === purchase.unit)
      return {
        ...purchase,
        ...fields,
        ...place(fields.storage_place_id),
        id: allocate(),
        unit_id: purchase.unit_id ?? unit?.id,
        remaining: fields.quantity,
      }
    })
    patch[pantry] = [...list(pantry), ...added]
    patch[purchases] = []
    patch[header] = null
  } else if (resource.startsWith('purchases/')) {
    const id = Number(resource.split('/')[1])
    const items = list(purchases)
    itemRequired(items, id)
    patch[purchases] = items.filter((item) => item.id !== id)
  } else if (resource === 'products/move') {
    const items = list(pantry)
    result = body.item_ids.map((id) => ({
      ...itemRequired(items, id),
      ...place(body.storage_place_id),
    }))
    const byId = new Map(result.map((item) => [item.id, item]))
    patch[pantry] = items.map((item) => byId.get(item.id) ?? item)
  } else {
    const [, rawId, action] = resource.split('/')
    const items = list(pantry)
    const current = itemRequired(items, Number(rawId))
    if (method === 'PATCH') {
      result = {
        ...current,
        ...itemFields(body),
        ...place(body.storage_place_id ?? current.storage_place_id),
        quantity: Math.max(body.quantity, current.quantity + body.quantity - current.remaining),
        remaining: body.quantity,
      }
    } else if (body.reason === 'mistake') {
      result = { ...current, is_deleted: true }
    } else {
      const quantity = body.quantity ?? current.remaining
      if (quantity > current.remaining) throw new Error('Недостаточно продукта в кладовой')
      const remaining = Number((current.remaining - quantity).toFixed(6))
      result = {
        ...current,
        remaining,
        is_over: remaining === 0,
        is_consumed: remaining === 0 && action === 'consumption',
        is_wasted: remaining === 0 && action === 'waste',
      }
    }
    patch[pantry] = items.flatMap((item) => {
      if (item.id !== current.id) return [item]
      return result.is_over || result.is_deleted ? [] : [result]
    })
  }
  for (const [key, value] of Object.entries(patch)) {
    if (!Array.isArray(value)) {
      patch[key] = { value }
      continue
    }
    const before = new Map(data[key].map((item) => [item.id, item]))
    const after = new Set(value.map((item) => item.id))
    patch[key] = {
      remove: [...before.keys()].filter((id) => !after.has(id)),
      upsert: value.filter((item) => before.get(item.id) !== item),
    }
  }
  return { patch, ids, nextId, result }
}

export function serverOperation(operation, mapping) {
  const resolve = (id) => {
    if (id >= 0) return id
    if (mapping[id] === undefined) throw new Error('Не найден серверный номер позиции')
    return mapping[id]
  }
  const path = operation.path.replace(/\/(-\d+)(?=\/|$)/g, (_, id) => '/' + resolve(Number(id)))
  let { body } = operation
  if (body?.item_ids) body = { ...body, item_ids: body.item_ids.map(resolve) }
  if (body?.items) body = { ...body, items: body.items.map((item) => ({ ...item, id: resolve(item.id) })) }
  return { path, body }
}

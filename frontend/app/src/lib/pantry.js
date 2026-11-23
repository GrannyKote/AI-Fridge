export const SOON_THRESHOLD_DAYS = 4

const MS_IN_DAY = 24 * 60 * 60 * 1000

export function daysUntil(bestBefore) {
  const target = new Date(`${bestBefore}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return Math.round((target - today) / MS_IN_DAY)
}

function catalogDays(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const days = Number(value)
  return Number.isInteger(days) && days >= 0 ? days : null
}

// У продукта может быть свой срок предупреждения из справочника.
export function soonThresholdOf(item) {
  return catalogDays(item?.first_reminder_days) ?? SOON_THRESHOLD_DAYS
}

export function statusOf(item) {
  const days = daysUntil(item.best_before)

  if (days < 0) {
    return 'expired'
  }

  return days <= soonThresholdOf(item) ? 'soon' : 'fresh'
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function toIsoFromParts(year, month, day) {
  const date = new Date(year, month - 1, day)

  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return ''
  }

  return `${year}-${pad2(month)}-${pad2(day)}`
}

export function toIsoDate(value) {
  if (!value) {
    return ''
  }

  const iso = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (iso) {
    return toIsoFromParts(Number(iso[1]), Number(iso[2]), Number(iso[3]))
  }

  const display = String(value).match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (display) {
    return toIsoFromParts(Number(display[3]), Number(display[2]), Number(display[1]))
  }

  return ''
}

export function toDisplayDate(iso) {
  const value = toIsoDate(iso)

  if (!value) {
    return ''
  }

  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

export function maskDateInput(raw) {
  const digits = String(raw).replace(/\D/g, '').slice(0, 8)
  const day = digits.slice(0, 2)
  const month = digits.slice(2, 4)
  const year = digits.slice(4, 8)

  if (digits.length <= 2) {
    return day
  }
  if (digits.length <= 4) {
    return `${day}/${month}`
  }

  return `${day}/${month}/${year}`
}

// Дата в ISO по локальному времени: база плюс сдвиг в днях.
export function dateAfterDays(days = 0, from) {
  const iso = toIsoDate(from)
  const date = iso ? new Date(`${iso}T00:00:00`) : new Date()

  if (Number.isNaN(date.getTime())) {
    return dateAfterDays(days)
  }

  date.setDate(date.getDate() + days)

  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

// Срок годности по умолчанию: сегодня плюс expires_in из справочника.
export function defaultBestBeforeOf(product) {
  const days = catalogDays(product?.expires_in)
  return days === null ? '' : dateAfterDays(days)
}

export function daysWord(count) {
  const tail = count % 10
  const hundreds = count % 100

  if (tail === 1 && hundreds !== 11) {
    return 'день'
  }
  if (tail >= 2 && tail <= 4 && (hundreds < 12 || hundreds > 14)) {
    return 'дня'
  }

  return 'дней'
}

function pluralDays(count) {
  return `${count} ${daysWord(count)}`
}

export function badgeTextOf(item) {
  const days = daysUntil(item.best_before)

  if (days < 0) {
    return `Просрочен ${pluralDays(-days)}`
  }
  if (days === 0) {
    return 'Истекает сегодня'
  }

  return pluralDays(days)
}

export function displayProductName(name) {
  const value = String(name ?? '').trim()
  return value ? value[0].toLocaleUpperCase('ru') + value.slice(1) : ''
}

export function formatNumber(value) {
  const number = Number(value)

  return Number.isInteger(number) ? String(number) : String(Number(number.toFixed(3)))
}

// Цену указывать необязательно, поэтому пустое значение превращается в пустую строку.
export function formatPrice(value) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  const number = Number(value)

  if (!Number.isFinite(number)) {
    return ''
  }

  return `${Number.isInteger(number) ? number : number.toFixed(2)} ₽`
}

// Совпадает с посевом unit_of_measurement: шт, г, мл.
export const FALLBACK_UNITS = [
  { id: 1, name: 'шт' },
  { id: 2, name: 'г' },
  { id: 3, name: 'мл' },
]

const DEFAULT_QUANTITY_BY_UNIT = {
  шт: '1',
  г: '1000',
  мл: '1000',
}

export function defaultQuantityForUnit(unitName) {
  return DEFAULT_QUANTITY_BY_UNIT[unitName] ?? '1'
}

// В карточке показываем остаток: часть продукта могли уже употребить или списать.
export function formatAmount(item) {
  const value = formatNumber(item.remaining ?? item.quantity)

  return item.unit ? `${value} ${item.unit}` : value
}

export function actionAmount(raw, unit) {
  const amount = parseAmount(raw)

  if (!Number.isFinite(amount) || amount <= 0) {
    return ''
  }

  return unit ? `${formatNumber(amount)} ${unit}` : formatNumber(amount)
}

const MONTHS = [
  'янв.',
  'фев.',
  'мар.',
  'апр.',
  'мая',
  'июн.',
  'июл.',
  'авг.',
  'сен.',
  'окт.',
  'ноя.',
  'дек.',
]

export function formatShortDate(bestBefore) {
  const date = new Date(`${bestBefore}T00:00:00`)

  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

const PLACE_SHORT = {
  Холодильник: 'Холод.',
  Морозилка: 'Мороз.',
  Шкаф: 'Шкаф',
  Бакалея: 'Бакалея',
  Специи: 'Специи',
  Консервы: 'Консервы',
}

export function shortPlaceOf(name) {
  if (!name) {
    return ''
  }

  return PLACE_SHORT[name] ?? name.split(/\s+/)[0]
}

// Срок годности хранится датой, поэтому продукт считается годным до её конца.
function hoursUntil(bestBefore) {
  const end = new Date(`${bestBefore}T00:00:00`)
  end.setDate(end.getDate() + 1)

  return Math.max(0, Math.ceil((end - Date.now()) / 3_600_000))
}

export function deadlineText(item) {
  const days = daysUntil(item.best_before)

  if (days < 0) {
    return `Просрочен ${-days} дн.`
  }
  if (days === 0) {
    return `${hoursUntil(item.best_before)} ч.`
  }

  return `${days} дн.`
}

// Крупный счётчик справа: сколько дней осталось или сколько прошло с конца срока.
export function deadlineCounter(item) {
  const days = daysUntil(item.best_before)

  if (days < 0) {
    return { value: -days, label: 'дн. назад', status: 'expired' }
  }

  const left = Math.max(days, 1)

  return { value: left, label: daysWord(left), status: statusOf(item) }
}

export function parseAmount(raw) {
  return Number(String(raw).replace(',', '.'))
}

export function amountError(raw, available, unit) {
  const value = parseAmount(raw)

  if (String(raw).trim() === '') {
    return 'Введите количество'
  }
  if (!Number.isFinite(value) || value <= 0) {
    return 'Количество должно быть больше нуля'
  }
  if (value > available) {
    return `Доступно только ${formatNumber(available)}${unit ? ` ${unit}` : ''}`
  }

  return ''
}

const CATEGORY_VIEW = {
  Молочные: { emoji: '🥛', tone: 'dairy' },
  'Мясо и рыба': { emoji: '🥩', tone: 'meat' },
  'Крупы и макароны': { emoji: '🍚', tone: 'grocery' },
  'Соусы и специи': { emoji: '🧂', tone: 'sauce' },
  Яйца: { emoji: '🥚', tone: 'eggs' },
  'Хлеб и выпечка': { emoji: '🍞', tone: 'bread' },
}

const TONES = ['dairy', 'meat', 'grocery', 'sauce', 'eggs', 'bread']

export function categoryView(name, id = 0) {
  return CATEGORY_VIEW[name] ?? { emoji: '🍽️', tone: TONES[id % TONES.length] }
}

function lotKey(item) {
  // Temporary entries have no server lot identity until synchronization.
  if (item.id < 0) return `local:${item.id}`
  return [
    item.product_id ?? '',
    String(item.name ?? '').trim().toLowerCase(),
    item.best_before ?? '',
    item.unit_id ?? item.unit ?? '',
    item.storage_place_id ?? '',
  ].join('\u0001')
}

function sumPrices(items) {
  let total = 0
  let hasPrice = false

  for (const item of items) {
    if (item.price === null || item.price === undefined || item.price === '') {
      continue
    }

    const value = Number(item.price)
    if (!Number.isFinite(value)) {
      continue
    }

    total += value
    hasPrice = true
  }

  return hasPrice ? total : null
}

// Одинаковые позиции в кладовой показываем одной карточкой.
export function mergeMatchingProducts(items) {
  const groups = new Map()

  for (const item of items) {
    const key = lotKey(item)
    const group = groups.get(key)

    if (group) {
      group.push(item)
    } else {
      groups.set(key, [item])
    }
  }

  return [...groups.values()].map((group) => {
    if (group.length === 1) {
      return group[0]
    }

    const sorted = [...group].sort((a, b) => a.id - b.id)

    return {
      ...sorted[0],
      quantity: sorted.reduce((sum, item) => sum + Number(item.quantity), 0),
      remaining: sorted.reduce((sum, item) => sum + Number(item.remaining ?? item.quantity), 0),
      price: sumPrices(sorted),
      is_over: sorted.every((item) => item.is_over),
      is_consumed: sorted.every((item) => item.is_consumed),
      is_wasted: sorted.every((item) => item.is_wasted),
      is_deleted: sorted.every((item) => item.is_deleted),
    }
  })
}

export function addPantryItem(list, item) {
  return mergeMatchingProducts([...list, item])
}

export function replacePantryLot(list, item) {
  const next = list.filter((product) => lotKey(product) !== lotKey(item))

  if (item.is_over || item.is_deleted) {
    return next
  }

  return [...next, item]
}

export function removePantryLot(list, item) {
  return list.filter((product) => lotKey(product) !== lotKey(item))
}

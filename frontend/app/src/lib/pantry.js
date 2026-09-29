export const SOON_THRESHOLD_DAYS = 4

export function localDate(value = new Date()) {
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}

export function quantityForUnit(name) {
  if (name === 'шт') return '1'
  if (name === 'г' || name === 'мл') return '1000'
  return null
}

const MS_IN_DAY = 24 * 60 * 60 * 1000

export function dateFromIso(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso ?? ''))
  if (!match) {
    return new Date()
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

export function expiryDate(days, from = new Date()) {
  const date = new Date(from.getFullYear(), from.getMonth(), from.getDate())
  date.setDate(date.getDate() + days)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function daysUntil(bestBefore) {
  const target = new Date(`${bestBefore}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return Math.round((target - today) / MS_IN_DAY)
}

export function statusOf(item) {
  const days = daysUntil(item.best_before)

  if (days < 0) {
    return 'expired'
  }

  return days <= SOON_THRESHOLD_DAYS ? 'soon' : 'fresh'
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

export function formatNumber(value) {
  const number = Number(value)

  return Number.isInteger(number) ? String(number) : String(Number(number.toFixed(3)))
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

export function formatRuDate(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso ?? ''))
  if (!match) {
    return ''
  }
  return `${match[3]}.${match[2]}.${match[1]}`
}

export function maskRuDate(raw) {
  const digits = String(raw ?? '').replace(/\D/g, '').slice(0, 8)
  if (digits.length <= 2) {
    return digits
  }
  if (digits.length <= 4) {
    return `${digits.slice(0, 2)}.${digits.slice(2)}`
  }
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`
}

export function parseRuDate(text) {
  const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(String(text ?? '').trim())
  if (!match) {
    return ''
  }
  const day = Number(match[1])
  const month = Number(match[2])
  const year = Number(match[3])
  const date = new Date(year, month - 1, day)
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return ''
  }
  return `${match[3]}-${match[2]}-${match[1]}`
}

export function draftExpiryLabel(days, from = new Date()) {
  if (!Number.isInteger(days) || days <= 0) {
    return ''
  }
  return formatRuDate(expiryDate(days, from))
}

export function formatShortDate(bestBefore) {
  return formatRuDate(bestBefore)
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

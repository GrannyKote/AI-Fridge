export const SOON_THRESHOLD_DAYS = 4

const MS_IN_DAY = 24 * 60 * 60 * 1000

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

function pluralDays(count) {
  const tail = count % 10
  const hundreds = count % 100

  if (tail === 1 && hundreds !== 11) {
    return `${count} день`
  }
  if (tail >= 2 && tail <= 4 && (hundreds < 12 || hundreds > 14)) {
    return `${count} дня`
  }

  return `${count} дней`
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

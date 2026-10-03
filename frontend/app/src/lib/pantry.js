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

// Дата для <input type="date"> по локальному времени: сегодня плюс сдвиг в днях.
export function dateAfterDays(days = 0) {
  const date = new Date()
  date.setDate(date.getDate() + days)

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${date.getFullYear()}-${month}-${day}`
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

  return `${date.getDate()} ${MONTHS[date.getMonth()]}`
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

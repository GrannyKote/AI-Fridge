import { useEffect, useMemo, useState } from 'react'
import { formatRuDate } from '../lib/pantry.js'
import { shoppingApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { ArrowLeftIcon, ArrowRightIcon } from './icons.jsx'
import '../styles/dialog.css'
import '../styles/shopping.css'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const MONTHS = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
]
function toKey(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function parseKey(key) {
  const [year, month, day] = key.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function shiftMonth(date, delta) {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1)
}

function mondayOffset(date) {
  const weekday = date.getDay()
  return weekday === 0 ? 6 : weekday - 1
}

function formatPlanDate(key) {
  return formatRuDate(key)
}

export function PlanPurchaseDialog({ groupId, onClose, onPlanned }) {
  const todayKey = toKey(new Date())
  const [view, setView] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const [selected, setSelected] = useState(todayKey)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  useEffect(() => {
    let cancelled = false

    shoppingApi
      .header(groupId)
      .then((header) => {
        if (cancelled || !header.plan_date) {
          return
        }

        const planned = parseKey(header.plan_date)
        setSelected(header.plan_date)
        setView(new Date(planned.getFullYear(), planned.getMonth(), 1))
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [groupId])

  const cells = useMemo(() => {
    const first = new Date(view.getFullYear(), view.getMonth(), 1)
    const days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate()
    const blanks = mondayOffset(first)

    return [
      ...Array.from({ length: blanks }, () => null),
      ...Array.from({ length: days }, (_, index) => {
        const date = new Date(view.getFullYear(), view.getMonth(), index + 1)
        return { day: index + 1, key: toKey(date) }
      }),
    ]
  }, [view])

  async function handleSelect() {
    setError('')
    setPending(true)

    try {
      await shoppingApi.setPlanDate(groupId, selected)
      onPlanned(formatPlanDate(selected))
    } catch (planError) {
      setError(planError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div
      className="dialog dialog--page"
      role="dialog"
      aria-modal="true"
      aria-labelledby="plan-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="add planner">
        <header className="planner__top">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
        </header>

        <h2 className="planner__title" id="plan-title">
          Планировщик покупок
        </h2>
        <p className="planner__hint">Укажи дату — подберём список</p>

        <div className="cal">
          <div className="cal__nav">
            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setView((current) => shiftMonth(current, -1))}
              aria-label="Предыдущий месяц"
            >
              <ArrowLeftIcon />
            </button>
            <p className="cal__month">
              {MONTHS[view.getMonth()]} {view.getFullYear()} г.
            </p>
            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setView((current) => shiftMonth(current, 1))}
              aria-label="Следующий месяц"
            >
              <ArrowRightIcon />
            </button>
          </div>

          <div className="cal__week" aria-hidden="true">
            {WEEKDAYS.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>

          <div className="cal__grid">
            {cells.map((cell, index) =>
              cell ? (
                <button
                  key={cell.key}
                  className={`cal__day${cell.key === todayKey ? ' is-today' : ''}${
                    cell.key === selected ? ' is-selected' : ''
                  }`}
                  type="button"
                  onClick={() => setSelected(cell.key)}
                  aria-pressed={cell.key === selected}
                  aria-current={cell.key === todayKey ? 'date' : undefined}
                >
                  {cell.day}
                </button>
              ) : (
                <span key={`empty-${index}`} className="cal__empty" />
              ),
            )}
          </div>
        </div>

        <FormAlert>{error}</FormAlert>

        <button className="btn btn--primary planner__submit" type="button" onClick={handleSelect} disabled={pending}>
          {pending ? 'Сохраняем...' : 'Выбрать'}
        </button>
      </div>
    </div>
  )
}

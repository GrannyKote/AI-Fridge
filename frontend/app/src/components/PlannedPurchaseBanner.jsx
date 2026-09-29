import { CalendarIcon, CartIcon } from './icons.jsx'
import { daysUntil, daysWord, formatRuDate } from '../lib/pantry.js'

function formatPlanHeading(planDate) {
  return formatRuDate(planDate)
}

function formatCountdown(planDate) {
  const days = daysUntil(planDate)

  if (days === 0) {
    return 'Сегодня'
  }
  if (days === 1) {
    return 'Завтра'
  }
  if (days > 1) {
    return `Через ${days} ${daysWord(days)}`
  }
  if (days === -1) {
    return 'Вчера'
  }

  return `${-days} ${daysWord(-days)} назад`
}

export function PlannedPurchaseBanner({ planDate, onChangeDate, onCalculate }) {
  return (
    <section className="plan-banner" aria-label="Запланированная покупка">
      <div className="plan-card">
        <button className="plan-card__info" type="button" onClick={onChangeDate} aria-label="Изменить дату покупки">
          <span className="plan-card__icon" aria-hidden="true">
            <CalendarIcon />
          </span>
          <span className="plan-card__text">
            <span className="plan-card__date">{formatPlanHeading(planDate)}</span>
            <span className="plan-card__eta">{formatCountdown(planDate)}</span>
          </span>
        </button>

        <button className="plan-card__calc" type="button" onClick={onCalculate}>
          <CartIcon />
          Рассчитать
        </button>
      </div>
    </section>
  )
}

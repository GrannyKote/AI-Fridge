import { ClockIcon } from './icons.jsx'
import {
  categoryView,
  deadlineCounter,
  deadlineText,
  formatAmount,
  formatShortDate,
  statusOf,
} from '../lib/pantry.js'

export function ForecastCard({ product }) {
  const status = statusOf(product)
  const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)
  const counter = deadlineCounter(product)

  return (
    <article className={`fcard${status === 'expired' ? ' fcard--expired' : ''}`}>
      <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
        {emoji}
      </div>

      <div className="fcard__body">
        <h3 className="card__title">{product.name}</h3>
        <p className={`fcard__deadline fcard__deadline--${status}`}>
          <ClockIcon />
          {deadlineText(product)}
        </p>
        <p className="fcard__meta">
          {formatAmount(product)} · Годен до {formatShortDate(product.best_before)}
        </p>
      </div>

      <p className={`fcard__counter fcard__counter--${counter.status}`}>
        <span className="fcard__value">{counter.value}</span>
        <span className="fcard__label">{counter.label}</span>
      </p>
    </article>
  )
}

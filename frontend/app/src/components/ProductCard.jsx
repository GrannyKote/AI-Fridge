import { TrashIcon, UtensilsIcon } from './icons.jsx'
import { badgeTextOf, categoryView, formatAmount, statusOf } from '../lib/pantry.js'

export function ProductCard({ product, onAction }) {
  const status = statusOf(product)
  const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)

  return (
    <article className={`card${status === 'expired' ? ' card--expired' : ''}`}>
      <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
        {emoji}
      </div>

      <div className="card__body">
        <h3 className="card__title">{product.name}</h3>
        <p className="card__meta">
          <span>{formatAmount(product)}</span>
          <span className="card__dot" aria-hidden="true">
            ·
          </span>
          <span className={`card__badge card__badge--${status}`}>{badgeTextOf(product)}</span>
        </p>
      </div>

      <div className="card__actions">
        <button
          className="icon-btn"
          type="button"
          onClick={() => onAction(product, 'use')}
          aria-label={`Использовать «${product.name}»`}
        >
          <UtensilsIcon />
        </button>
        <button
          className="icon-btn icon-btn--danger"
          type="button"
          onClick={() => onAction(product, 'delete')}
          aria-label={`Удалить «${product.name}»`}
        >
          <TrashIcon />
        </button>
      </div>
    </article>
  )
}
